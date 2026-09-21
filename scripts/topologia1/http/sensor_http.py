#!/usr/bin/env python3
"""
Sensor de classificacao de mosquitos na borda — ramificacao HTTP.

Mesmo pipeline das ramificacoes MQTT/CoAP (sensoriamento.py compartilhado):
le audio real do dataset na RAM em tempo real, roda o modelo Residual na borda
e envia APENAS o metadado da classificacao via HTTP POST (/meta) ao servidor.

Uso:
  python3 sensor_http.py --url http://11.0.0.10:8000/meta --id sta0 --cluster 1
"""

import argparse
import json
import os
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)                       # sensoriamento.py
sys.path.insert(0, os.path.join(_BASE, 'ml'))   # classificador.py

import numpy as np  # noqa: E402

from classificador import Classificador  # noqa: E402
from sensoriamento import (  # noqa: E402
    DATASET_RAM, capturar_amostra_de_audio, descritores, montar_metadado)

TIMEOUT_S = 5.0
MAX_ERROS = 3


def parse_args():
    p = argparse.ArgumentParser(
        description='Sensor de audio real com classificacao na borda (HTTP)')
    p.add_argument('--url', default='http://11.0.0.10:8000/meta',
                   help='Endpoint POST do servidor')
    p.add_argument('--id', default='sta0', help='ID do sensor')
    p.add_argument('--cluster', type=int, default=1, help='Cluster do sensor')
    p.add_argument('--interval', type=float, default=3.0,
                   help='Intervalo entre ciclos (s)')
    p.add_argument('--dataset', default=DATASET_RAM, help='Dir RAM (tmpfs) do dataset')
    p.add_argument('--tempo-real', default=True, action=argparse.BooleanOptionalAction,
                   help='Le o audio em tempo real (1s por 1s de audio; default on)')
    p.add_argument('--nocount', type=int, default=0,
                   help='Quantos ciclos rodar antes de sair (0 = infinito)')
    return p.parse_args()


def main():
    args = parse_args()
    sensor_id = args.id
    rng = np.random.default_rng(
        int(sensor_id) if str(sensor_id).isdigit() else sum(ord(c) for c in sensor_id))
    classificador = Classificador()

    count = 0
    erros = 0
    while True:
        classe_real, janela_inicial, indice, janela = capturar_amostra_de_audio(
            rng, args.dataset, tempo_real=args.tempo_real)
        probs, classe = classificador.classificar(janela)
        freq, rms = descritores(janela)
        meta = montar_metadado(classe_real, indice, probs, classe, freq, rms,
                               count + 1, 'sta%s' % sensor_id, args.cluster,
                               janela_inicial=janela_inicial)
        try:
            req = urllib.request.Request(
                args.url,
                data=json.dumps(meta).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                resp.read()
            count += 1
            erros = 0
        except OSError:
            erros += 1
            if erros >= MAX_ERROS:
                break

        if args.nocount and count >= args.nocount:
            break
        time.sleep(args.interval)


if __name__ == '__main__':
    main()