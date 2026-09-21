#!/usr/bin/env python3
"""
Sensor de classificacao de mosquitos na borda — ramificacao CoAP.

Mesmo pipeline das ramificacoes MQTT/HTTP (sensoriamento.py compartilhado):
le audio real do dataset na RAM em tempo real, roda o modelo Residual na borda
e envia APENAS o metadado da classificacao via CoAP POST /meta (UDP) ao
servidor. CON por padrao (entrega garantida); `--non` usa mensagens nao
confirmaveis.

Uso:
  python3 sensor_coap.py --url coap://11.0.0.10:5683/meta --id sta0 --cluster 1
"""

import argparse
import asyncio
import json
import os
import sys

import aiocoap

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)                       # sensoriamento.py
sys.path.insert(0, os.path.join(_BASE, 'ml'))   # classificador.py

import numpy as np  # noqa: E402

from classificador import Classificador  # noqa: E402
from sensoriamento import (  # noqa: E402
    DATASET_RAM, capturar_amostra_de_audio, descritores, montar_metadado)

ATTEMPT_TIMEOUT = 6.0
MAX_ERROS = 3


def parse_args():
    p = argparse.ArgumentParser(
        description='Sensor de audio real com classificacao na borda (CoAP)')
    p.add_argument('--url', default='coap://11.0.0.10:5683/meta',
                   help='Endpoint CoAP do servidor (POST /meta)')
    p.add_argument('--id', default='sta0', help='ID do sensor')
    p.add_argument('--cluster', type=int, default=1, help='Cluster do sensor')
    p.add_argument('--interval', type=float, default=3.0,
                   help='Intervalo entre ciclos (s)')
    p.add_argument('--dataset', default=DATASET_RAM, help='Dir RAM (tmpfs) do dataset')
    p.add_argument('--tempo-real', default=True, action=argparse.BooleanOptionalAction,
                   help='Le o audio em tempo real (1s por 1s de audio; default on)')
    p.add_argument('--non', action='store_true',
                   help='Usar mensagens CoAP nao confirmaveis (NON)')
    p.add_argument('--nocount', type=int, default=0,
                   help='Quantos ciclos rodar antes de sair (0 = infinito)')
    return p.parse_args()


async def publicar(ctx, url, mtype, payload):
    msg = aiocoap.Message(
        code=aiocoap.POST,
        uri=url,
        payload=json.dumps(payload).encode('utf-8'),
    )
    if mtype is not None:
        msg.mtype = mtype
    req = ctx.request(msg)
    resp = await asyncio.wait_for(req.response, timeout=ATTEMPT_TIMEOUT)
    return resp.code


async def run(args):
    sensor_id = args.id
    rng = np.random.default_rng(
        int(sensor_id) if str(sensor_id).isdigit() else sum(ord(c) for c in sensor_id))
    mtype = aiocoap.NON if args.non else None
    classificador = Classificador()

    ctx = await aiocoap.Context.create_client_context()

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
            code = await publicar(ctx, args.url, mtype, meta)
            count += 1
            erros = 0
        except (asyncio.TimeoutError, OSError, ConnectionError):
            erros += 1
            if erros >= MAX_ERROS:
                break

        if args.nocount and count >= args.nocount:
            break
        await asyncio.sleep(args.interval)

    await ctx.shutdown()


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()