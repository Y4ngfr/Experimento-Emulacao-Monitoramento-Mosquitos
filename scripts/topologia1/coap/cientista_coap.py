#!/usr/bin/env python3
"""
Cientista (assinante CoAP) — ramificacao CoAP.

Usa o motor compartilhado metricas_app.py (mesmo CSV de aplicacao das outras
ramificacoes). Registra Observe no recurso /stream do servidor e recebe
notificacoes push a cada metadado produzido pelos sensores.

Uso:
  python3 cientista_coap.py --url coap://11.0.0.10:5683/stream --id cient1 \
      --log /app/dados/coap/cient1.log [--metrics=/app/dados/metricas/app]
"""

import argparse
import asyncio
import json
import os
import sys

import aiocoap
import aiocoap.error

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)

from metricas_app import AppMetricas  # noqa: E402

MAX_ERROS = 5
ERRO_SLEEP = 2.0


def parse_args():
    p = argparse.ArgumentParser(description='Cientista CoAP subscriber (Observe)')
    p.add_argument('--url', default='coap://11.0.0.10:5683/stream',
                   help='Endpoint CoAP do recurso /stream')
    p.add_argument('--id', default='cient0', help='ID do cientista')
    p.add_argument('--log', default='/app/dados/coap/cient0.log', help='Arquivo de log')
    p.add_argument('--metrics', default=None, help='Dir para o CSV de metricas de app')
    p.add_argument('--window', type=int, default=20, help='Mensagens por linha do CSV de metricas')
    return p.parse_args()


async def _observe_iter(ctx, url):
    req = aiocoap.Message(code=aiocoap.GET, uri=url)
    req.opt.observe = 0
    requester = ctx.request(req)
    await requester.response
    obs = requester.observation
    if obs is None:
        raise ConnectionError('servidor nao aceitou Observe')
    async for notif in obs:
        yield notif


async def run(args):
    m = AppMetricas(name=args.id, log=args.log, metrics_dir=args.metrics,
                    window=args.window)
    ctx = await aiocoap.Context.create_client_context()
    erros = 0

    while True:
        try:
            async for notif in _observe_iter(ctx, args.url):
                erros = 0
                try:
                    info = json.loads(notif.payload.decode('utf-8'))
                except ValueError:
                    continue
                meta = info.get('meta')
                if meta is None:
                    continue
                m.registrar(json.dumps(meta), meta.get('sensor', '?'))
        except (OSError, asyncio.TimeoutError, aiocoap.error.ObservationCancelled,
                aiocoap.error.TimeoutError, ConnectionError):
            erros += 1
            if erros >= MAX_ERROS:
                break
            await asyncio.sleep(ERRO_SLEEP)
            continue
        except Exception as e:  # noqa: BLE001
            erros += 1
            if erros >= MAX_ERROS:
                break
            await asyncio.sleep(ERRO_SLEEP)
            continue

    await ctx.shutdown()


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()