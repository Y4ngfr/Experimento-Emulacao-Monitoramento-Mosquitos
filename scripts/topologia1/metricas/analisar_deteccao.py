#!/usr/bin/env python3
"""
Analisa a deteccao dos sensores a partir dos metadados coletados.

Cada metadado carrega 'classe_real' (classe do audio ouvido) e 'correto'
(predicao == classe real, marcado pelo proprio sensor). Este script le os
logs de metadados (meta.log dos servidores HTTP/CoAP e/ou cient*.log das
3 ramificacoes) e consolida:

  - taxa de deteccao por classe real (corretas / observadas);
  - acuracia por sensor;
  - acuracia geral;
  - matriz de confusao (classe real x classe predita).

Como a distribuicao alvo por sensor e 50% ambiente / 30% femea / 10% macho /
10% outros, as proporcoes por classe tambem sao reportadas (para conferir o
sorteio).

Uso:
  python3 analisar_deteccao.py --dir /app/dados/experimentos/experimento_XXX
  python3 analisar_deteccao.py --dir /app/dados/experimentos/experimento_XXX/raw/c15_run1
  python3 analisar_deteccao.py --dir /app/dados/http
"""

import argparse
import json
import os
import sys

CLASSES = {
    0: 'macho',
    1: 'femea',
    2: 'outros',
    3: 'ambiente',
}

NOME_PARA_CLASSE = {
    'aedes_aegypti_macho': 0,
    'aedes_aegypti_femea': 1,
    'outros_mosquitos': 2,
    'ambiente': 3,
}


def ler_metadados(lines):
    """Extrai dicts JSON de linhas de log ('... [cient1] recebido de X: {...}')."""
    metas = []
    for line in lines:
        i = line.find('{')
        if i < 0:
            continue
        try:
            meta = json.loads(line[i:])
        except ValueError:
            continue
        if 'classe_real' not in meta and 'sensor' not in meta:
            continue
        metas.append(meta)
    return metas


def predita_para_indice(nome):
    """Normaliza o nome da classe predita para o indice inteiro 0..3."""
    if isinstance(nome, int) or (isinstance(nome, str) and nome.isdigit()):
        return int(nome)
    if nome in NOME_PARA_CLASSE:
        return NOME_PARA_CLASSE[nome]
    return None


def coletar(diretorio):
    """Descobre os logs de metadados em `diretorio` e retorna metadados dedup."""
    candidatos = []
    for root, _, files in os.walk(diretorio):
        for f in files:
            if f == 'meta.log' or (f.startswith('cient') and f.endswith('.log')):
                candidatos.append(os.path.join(root, f))
    if not candidatos:
        return []

    metas = []
    vistos = set()
    for path in sorted(candidatos):
        with open(path, encoding='utf-8', errors='replace') as f:
            for meta in ler_metadados(f):
                chave = (meta.get('sensor'), meta.get('seq'))
                if chave in vistos:
                    continue
                vistos.add(chave)
                real = meta.get('classe_real')
                if real is None:
                    continue
                pred = predita_para_indice(meta.get('classe'))
                if pred is None and 'probs' in meta:
                    pred = int(max(range(len(meta['probs'])),
                                   key=lambda k: meta['probs'][k]))
                if pred is not None:
                    meta['_pred'] = pred
                metas.append(meta)
    return metas


def analisar(diretorio):
    metas = coletar(diretorio)
    if not metas:
        print('Nenhum metadado encontrado em %s (procure por meta.log ou cient*.log)' % diretorio)
        return

    por_classe = {c: {'n': 0, 'ok': 0} for c in CLASSES}
    por_sensor = {}
    matriz = {real: {pred: 0 for pred in CLASSES} for real in CLASSES}

    for meta in metas:
        real = int(meta['classe_real'])
        pred = meta.get('_pred')
        ok = bool(meta.get('correto', pred == real)) if pred is not None else bool(meta.get('correto', False))
        if pred is None:
            continue
        por_classe[real]['n'] += 1
        por_classe[real]['ok'] += ok
        por_sensor.setdefault(meta['sensor'], {'n': 0, 'ok': 0})
        por_sensor[meta['sensor']]['n'] += 1
        por_sensor[meta['sensor']]['ok'] += ok
        matriz[real][pred] += 1

    total_n = sum(v['n'] for v in por_classe.values())
    total_ok = sum(v['ok'] for v in por_classe.values())

    print('=' * 66)
    print('DETECCAO POR CLASSE REAL  (n=%d metadados)' % total_n)
    print('=' * 66)
    for c in sorted(CLASSES):
        v = por_classe[c]
        taxa = 100.0 * v['ok'] / v['n'] if v['n'] else 0.0
        perc = 100.0 * v['n'] / total_n if total_n else 0.0
        print('  classe %d (%-8s): %4d obs | %4d corretas | deteccao %5.1f%% | '
              'proporcao amostrada %5.1f%%' % (c, CLASSES[c], v['n'], v['ok'], taxa, perc))

    print('=' * 66)
    print('ACURACIA POR SENSOR')
    print('=' * 66)
    for s in sorted(por_sensor):
        v = por_sensor[s]
        print('  %-8s %3d/%3d = %5.1f%%' % (s, v['ok'], v['n'], 100.0 * v['ok'] / v['n']))

    print('=' * 66)
    print('ACURACIA GERAL: %d/%d = %.2f%%' %
          (total_ok, total_n, 100.0 * total_ok / max(1, total_n)))
    print('=' * 66)
    print('MATRIZ DE CONFUSAO (real x predita)')
    print('-' * 66)
    header = '     ' + ''.join('  pred%d ' % p for p in sorted(CLASSES)) + '  n'
    print(header)
    for real in sorted(CLASSES):
        row = 'real%d' % real
        for pred in sorted(CLASSES):
            row += '   %5d ' % matriz[real][pred]
        row += '  %6d' % por_classe[real]['n']
        print(row)


def main():
    ap = argparse.ArgumentParser(description='Analisa taxa de deteccao e acuracia dos sensores')
    ap.add_argument('--dir', default='.',
                    help='Dir com meta.log / cient*.log (run ou /app/dados/<proto>)')
    args = ap.parse_args()
    analisar(args.dir)


if __name__ == '__main__':
    main()