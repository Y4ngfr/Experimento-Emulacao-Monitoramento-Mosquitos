#!/usr/bin/env python3
"""
Pré-processa o dataset de áudio para o modelo de classificação Residual.

Pipelines do modelo (ml/mel.py, espelha o treino):
  áudio 8kHz -> janela de 9984 amostras (1,248s) ->
  melspectrogram(512, n_fft=1024, hop=256) -> power_to_db(ref=max, top_db=80)/80+1 ->
  (1,513,40,1) float32.

Este script segmenta cada gravação em janelas de 9984 amostras e salva os
blocos de áudio float32 (em [-1,1]) em Dataset-processado/<classe>/<i>_<j>.npy
(i = índice do arquivo, j = offset da janela). A extração do mel (NumPy puro)
fica para a inferência, igual ao Classificador.classificar().

As pastas 0..3 do Dataset correspondem a:
  0 = aedes_aegypti_macho, 1 = aedes_aegypti_femea, 2 = outros_mosquitos, 3 = ambiente

Uso (dentro do container):
  python3 preparar_dataset.py
"""

import argparse
import json
import os

import librosa
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 8000
WINDOW = 9984
CLASSES = ['0', '1', '2', '3']
DEFAULT_DATASET_DIR = os.path.join(HERE, 'Dataset')
DEFAULT_OUTPUT_DIR = os.path.join(HERE, 'Dataset-processado')


def preparar(dataset_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    meta = {}
    total = 0
    for classe in CLASSES:
        classe_dir = os.path.join(dataset_dir, classe)
        output_classe_dir = os.path.join(output_dir, classe)
        os.makedirs(output_classe_dir, exist_ok=True)
        if not os.path.isdir(classe_dir):
            meta[classe] = {'arquivos': 0, 'janelas': 0, 'janelas_curtas': 0}
            continue

        arquivos = sorted(f for f in os.listdir(classe_dir) if f.endswith('.wav'))
        janelas = 0
        curtas = 0
        for i, arquivo in enumerate(arquivos):
            audio, _ = librosa.load(os.path.join(classe_dir, arquivo), sr=SR, mono=True)
            for j in range(0, len(audio) - WINDOW + 1, WINDOW):
                janela = audio[j:j + WINDOW].astype(np.float32)
                np.save(os.path.join(output_classe_dir, f'{i}_{j}.npy'), janela)
                janelas += 1
            if len(audio) < WINDOW:
                curtas += 1
        meta[classe] = {'arquivos': len(arquivos), 'janelas': janelas, 'janelas_curtas': curtas}
        total += janelas
        print('classe %s: %d arquivos -> %d janelas (%d curtas)'
              % (classe, len(arquivos), janelas, curtas), flush=True)

    with open(os.path.join(output_dir, 'meta.json'), 'w') as f:
        json.dump({'sr': SR, 'window': WINDOW, 'classes': meta, 'total_janelas': total},
                  f, indent=2)
    print('total de janelas: %d -> %s' % (total, output_dir))


def main():
    p = argparse.ArgumentParser(description='Pré-processa o dataset em janelas de 9984 amostras')
    p.add_argument('--dataset', default=DEFAULT_DATASET_DIR, help='dir do dataset bruto')
    p.add_argument('--output', default=DEFAULT_OUTPUT_DIR, help='dir do dataset processado')
    args = p.parse_args()
    preparar(args.dataset, args.output)


if __name__ == '__main__':
    main()