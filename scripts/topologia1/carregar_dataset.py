#!/usr/bin/env python3
"""
Empacota o Dataset-processado em um arquivo .bin por classe, direto no
tmpfs montado em RAM (/mnt/dataset-ram).

Cada .bin é um array float32 contíguo (janelas x 9984) lido pelos sensores
via numpy.memmap — as páginas já nascem na RAM do host (tmpfs). As classes
ficam em arquivos separados (0/2/3), como o dataset original.
M (/mnt/dataset-ram).

Cada .bin é um array float32 contíguo (janelas x 9984) lido pelos sensores
via numpy.memmap — as páginas já
Idempotente: só (re)escreve a classe se o .bin ainda não existir.

Uso (dentro do container, após montar o tmpfs):
  python3 carregar_dataset.py
"""

import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 8000
WINDOW = 9984
CLASSES = ['0', '1', '2', '3']
DEFAULT_SOURCE = os.path.join(HERE, 'Dataset-processado')
DEFAULT_DEST = '/mnt/dataset-ram'


def carregar(source_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    meta = {'sr': SR, 'window': WINDOW, 'classes': {}}
    total = 0
    for classe in CLASSES:
        classe_dir = os.path.join(source_dir, classe)
        destino = os.path.join(dest_dir, f'{classe}.bin')
        if not os.path.isdir(classe_dir):
            continue
        if os.path.exists(destino):
            janelas = os.path.getsize(destino) // (WINDOW * np.dtype(np.float32).itemsize)
            meta['classes'][classe] = {'count': janelas}
            total += janelas
            print('classe %s: ja existe (%d janelas) - %s' % (classe, janelas, destino),
                  flush=True)
            continue

        arquivos = sorted(f for f in os.listdir(classe_dir) if f.endswith('.npy'))
        if not arquivos:
            continue
        janelas = 0
        with open(destino, 'wb') as out:
            for arquivo in arquivos:
                janela = np.load(os.path.join(classe_dir, arquivo))
                out.write(np.ascontiguousarray(janela, dtype=np.float32).tobytes())
                janelas += 1
        meta['classes'][classe] = {'count': janelas}
        total += janelas
        print('classe %s: %d arquivos -> %d janelas %.1f MB em %s'
              % (classe, len(arquivos), janelas, janelas * WINDOW * 4 / 1e6, destino),
              flush=True)

    with open(os.path.join(dest_dir, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    print('total de janelas na RAM: %d -> %s' % (total, dest_dir))


def main():
    p = argparse.ArgumentParser(description='Empacota o dataset processado em .bin no tmpfs')
    p.add_argument('--source', default=DEFAULT_SOURCE, help='dir do Dataset-processado')
    p.add_argument('--dest', default=DEFAULT_DEST, help='dir RAM (tmpfs) de destino')
    args = p.parse_args()
    carregar(args.source, args.dest)


if __name__ == '__main__':
    main()