#!/usr/bin/env python3
"""
Sensor MQTT de classificacao de mosquitos na borda.

Mesmo pipeline das ramificacoes HTTP/CoAP (sensoriamento.py compartilhado):
le audio real do dataset na RAM em tempo real, roda o modelo Residual na borda
e publica APENAS o metadado da classificacao via MQTT em meta/clusterX/staY.

Uso:
  python3 sensor_pub.py --srvip 11.0.0.10 --id 0 --cluster 1
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import paho.mqtt.client as mqtt

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)                       # sensoriamento.py
sys.path.insert(0, os.path.join(_BASE, 'ml'))   # classificador.py

from classificador import Classificador  # noqa: E402
from sensoriamento import (  # noqa: E402
    DATASET_RAM, capturar_amostra_de_audio, descritores, montar_metadado)


def parse_args():
    p = argparse.ArgumentParser(description='Sensor MQTT de classificacao de mosquitos')
    p.add_argument('--srvip', default='11.0.0.10', help='IP do broker MQTT')
    p.add_argument('--id', default='sta0', help='Client ID do sensor')
    p.add_argument('--cluster', type=int, default=1, help='Numero do cluster (topico)')
    p.add_argument('--interval', type=float, default=3.0, help='Intervalo entre ciclos (s)')
    p.add_argument('--dataset', default=DATASET_RAM, help='Dir RAM (tmpfs) do dataset')
    p.add_argument('--tempo-real', default=True, action=argparse.BooleanOptionalAction,
                   help='Le o audio em tempo real (1s por 1s de audio; default on)')
    return p.parse_args()


def main():
    args = parse_args()
    sensor_id = args.id
    rng = np.random.default_rng(
        int(sensor_id) if str(sensor_id).isdigit() else sum(ord(c) for c in sensor_id))

    classificador = Classificador()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sta%s' % sensor_id)
    client.connect(args.srvip, 1883, 60)
    client.loop_start()

    seq = 0
    topico = 'meta/cluster%d/sta%s' % (args.cluster, sensor_id)
    while True:
        classe_real, janela_inicial, indice, janela = capturar_amostra_de_audio(
            rng, args.dataset, tempo_real=args.tempo_real)
        probs, classe = inferir_e_descrever(janela, classificador)
        freq, rms = descritores(janela)
        metadado = montar_metadado(classe_real, indice, probs, classe,
                                   freq, rms, seq + 1,
                                   'sta%s' % sensor_id, args.cluster,
                                   janela_inicial=janela_inicial)
        client.publish(topico, json.dumps(metadado), qos=1)
        seq += 1
        time.sleep(args.interval)


def inferir_e_descrever(janela, classificador):
    """Roda a inferencia do modelo na borda."""
    probs, classe = classificador.classificar(janela)
    return probs, classe


if __name__ == '__main__':
    main()