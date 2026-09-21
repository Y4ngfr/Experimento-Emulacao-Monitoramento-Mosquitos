#!/usr/bin/env python3
"""
grafico_barras.py — Graficos de barras das metricas por carga.

Le o metricas_por_run.csv de um experimento e gera, para cada metrica,
um grafico de barras em que o eixo X e a CARGA de sensores (10,20,30,40,50)
e o eixo Y e a MEDIA das runs para aquela metrica (com barra de erro =
desvio padrao entre as runs).

Uso (dentro do container):
  docker exec mininet-lab python3 /app/scripts/topologia1/metricas/grafico_barras.py \
      --csv /app/dados/experimentos/experimento_<ts>/metricas_por_run.csv

Opcoes:
  --csv       Caminho do metricas_por_run.csv (default: ultimo experimento)
  --out       Diretorio de saida dos PNGs (default: <dir do csv>/graficos)
  --cargas    Cargas a plotar no eixo X, separadas por virgula
              (default: as cargas presentes no CSV)
  --metricas  Metricas a plotar, separadas por virgula
              (default: todas as colunas numericas de metrica do CSV)
  --sem-erro  Nao desenhar a barra de erro (desvio padrao)
Sai e imprime uma tabela resumo (carga | media | desvio | n) para cada metrica.

Unidades de exibicao: metricas terminadas em '_ms' (latencia) e '_kbps'
(vazao) ja sao os valores do CSV nas unidades finais; CSVs legados com '_us'
ou '_bps' sao convertidos para ms / kb/s na plotagem. O CSV original nao e
alterado.
"""

import argparse
import csv
import os
import statistics
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Colunas que NAO sao metricas (identificadores/parametros do run)
NAO_METRICAS = {
    'experimento', 'protocolo', 'carga', 'run', 'n_aps', 'status', 'arquivo',
    'channel', 'raio_m', 'raio_min_m', 'dist_aps_m', 'sensores_por_ap',
    'tempo_s', 'inicio_ts', 'fim_ts', 'wall_s', 'mem_antes_mb',
    'falhas_assoc', 'n_app_csv', 'n_stas_csv',
}

# Conversao de unidade apenas para EXIBICAO (o CSV mantem seus valores).
# Os CSVs novos (experimento.py) ja gravam em ms e kb/s -> fator 1.0.
# Sufixos antigos de CSVs legados (_us, _bps) ainda sao convertidos:
#   _us  -> milissegundos (x 1e-3)
#   _bps -> kb/s (x 1e-3)  [as coletas calculam bits/s, bytes*8]
UNIDADES = {
    'kbps': ('kbps', 1.0),
    'bps':  ('kbps', 1e-3),
    'ms':   ('ms', 1.0),
    'us':   ('ms', 1e-3),
}


def fator_coluna(col):
    """(rotulo_do_eixo_y, fator) para uma coluna de metrica."""
    for suf, (rotulo, fator) in UNIDADES.items():
        if col.endswith('_' + suf):
            return '%s (%s)' % (col[:-(len(suf) + 1)], rotulo), fator
    return col, 1.0


def carregar(csv_path):
    with open(csv_path, newline='') as f:
        return list(csv.DictReader(f))


def colunas_metricas(rows):
    metricas = []
    for col in rows[0].keys():
        if col in NAO_METRICAS:
            continue
        for r in rows:
            v = r.get(col)
            if v is not None and v.strip() != '':
                try:
                    float(v)
                except ValueError:
                    break
                else:
                    metricas.append(col)
                    break
    return metricas


def valores_por_carga(rows, col):
    """{carga_int: [valores numericos das runs ok]}"""
    saida = {}
    for r in rows:
        if r.get('status') != 'ok':
            continue
        try:
            carga = int(r['carga'])
        except (ValueError, TypeError):
            continue
        v = r.get(col)
        try:
            saida.setdefault(carga, []).append(float(v))
        except (ValueError, TypeError):
            continue
    return saida


def media_desvio(vals):
    if not vals:
        return None, None
    media = statistics.mean(vals)
    if len(vals) >= 2:
        desvio = statistics.stdev(vals)
    else:
        desvio = None
    return media, desvio


def fmt_num(v):
    if v is None:
        return '--'
    a = abs(v)
    if a >= 10000 or (a > 0 and a < 0.01):
        return '%.3g' % v
    if a >= 100:
        return '%.1f' % v
    return '%.3g' % v


def plotar(metricas, cargas, dados, out_dir, com_erro):
    os.makedirs(out_dir, exist_ok=True)
    for met in metricas:
        por_carga = dados[met]
        rotulo, fator = fator_coluna(met)
        x = list(cargas)
        medias = []
        desvios = []
        for c in x:
            m, d = media_desvio(por_carga.get(c, []))
            medias.append(m * fator if m is not None else 0.0)
            desvios.append(d * fator if d is not None else None)
        plt.figure(figsize=(9, 5))
        pos = list(range(len(x)))
        barras = plt.bar(pos, medias, width=0.55,
                         color='#4c72b0', edgecolor='#2e4a7a')
        if com_erro:
            yerr = [0.0 if d is None else d for d in desvios]
            if any(yerr):
                plt.errorbar(pos, medias, yerr=yerr, fmt='none',
                             ecolor='#2e4a7a', capsize=3)
        for b, v, d in zip(barras, medias, desvios):
            plt.text(b.get_x() + b.get_width() / 2, v + (0.02 * max(medias) if max(medias) else 1),
                     fmt_num(v) + ('' if d is None else ' ±%s' % fmt_num(d)),
                     ha='center', va='bottom', fontsize=8)
        plt.xticks(pos, [str(c) for c in x])
        plt.xlabel('Carga (sensores)')
        plt.ylabel(rotulo)
        plt.title('Média das runs por carga — %s' % met)
        plt.grid(axis='y', alpha=0.3)
        arq = os.path.join(out_dir, '%s.png' % met)
        plt.savefig(arq, dpi=150, bbox_inches='tight')
        plt.close()
        print('gerado: %s' % arq)
        imprime_tabela(met, x, por_carga, fator)


def imprime_tabela(met, cargas, por_carga, fator=1.0):
    cab = '  %-28s | ' % 'carga'
    for c in cargas:
        cab += '%-16s' % c
    print(cab)
    print('  %-28s | %s' % ('', ' '.join(['%-16s' % 'media±desv(n)'] * len(cargas))))
    linha = '  %-28s | ' % met
    for c in cargas:
        m, d = media_desvio(por_carga.get(c, []))
        n = len(por_carga.get(c, []))
        mm = m * fator if m is not None else None
        dd = d * fator if d is not None else None
        linha += '%-16s' % ('%s±%s(%d)' % (fmt_num(mm), fmt_num(dd), n))
    print(linha)


def ultimo_csv():
    base = '/app/dados/experimentos'
    if os.path.isdir(base):
        exps = sorted((d for d in os.listdir(base) if d.startswith('experimento_')),
                      reverse=True)
        for e in exps:
            p = os.path.join(base, e, 'metricas_por_run.csv')
            if os.path.isfile(p):
                return p
    ap.error('--csv nao informado e nenhum experimento encontrado em %s' % base)


def main():
    global ap
    ap = argparse.ArgumentParser(description='Graficos de barras (media das runs) por carga')
    ap.add_argument('--csv', default=None, help='metricas_por_run.csv')
    ap.add_argument('--out', default=None, help='dir de saida dos PNGs')
    ap.add_argument('--cargas', default=None, help='cargas no eixo X, ex: 10,20,30,40,50')
    ap.add_argument('--metricas', default=None, help='metricas (colunas) a plotar')
    ap.add_argument('--sem-erro', action='store_true', help='sem barra de erro (desvio)')
    ap.add_argument('--todas', action='store_true',
                    help='forcar plotar todas as colunas numericas (default jah e todas)')
    args = ap.parse_args()

    csv_path = args.csv or ultimo_csv()
    if not os.path.isfile(csv_path):
        ap.error('CSV nao encontrado: %s' % csv_path)

    rows = carregar(csv_path)
    if not rows:
        ap.error('CSV vazio: %s' % csv_path)

    metricas = colunas_metricas(rows)
    if args.metricas:
        pedidas = [m.strip() for m in args.metricas.split(',') if m.strip()]
        faltando = [m for m in pedidas if m not in rows[0]]
        if faltando:
            ap.error('colunas inexistentes: %s' % ', '.join(faltando))
        metricas = pedidas

    cargas_presentes = sorted({int(r['carga']) for r in rows if r['carga']},
                              key=int)
    cargas = [int(c) for c in args.cargas.split(',')] if args.cargas else cargas_presentes

    dados = {m: valores_por_carga(rows, m) for m in metricas}
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(csv_path)), 'graficos')

    print('CSV: %s' % csv_path)
    print('Metricas: %d | cargas: %s | saída: %s' % (len(metricas), cargas, out_dir))
    plotar(metricas, cargas, dados, out_dir, com_erro=not args.sem_erro)


if __name__ == '__main__':
    main()