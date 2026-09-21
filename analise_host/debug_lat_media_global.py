#!/usr/bin/env python3
"""Recomputa e imprime a latencia media global real por run (mqtt/http/coap),
usando o mesmo filtro t0.warmup dos cient*.log. Quick-debug da metrica do grafico."""
import csv
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.topologia1.experimento import APPS_CIENT, _msg_log, ler_t0  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'dados', 'experimentos')

EXPERIMENTOS = {
    'mqtt': 'experimento_20260914_235110',
    'http': 'experimento_20260915_045417',
    'coap': 'experimento_20260915_073606',
}

for proto, exp in EXPERIMENTOS.items():
    print('===== %s (%s) =====' % (proto.upper(), exp))
    p = os.path.join(BASE, exp, 'metricas_por_run.csv')
    rows = list(csv.DictReader(open(p)))
    for r in rows:
        carga = r.get('carga', '').strip()
        if carga not in ('10', '30', '50'):
            continue
        run = r.get('run', '').strip()
        base_run = os.path.join(BASE, exp, run)
        app_dir = os.path.join(base_run, 'app')
        t0 = ler_t0(os.path.join(base_run, 'metricas'))
        lats = []
        for i in APPS_CIENT:
            clog = os.path.join(app_dir, 'cient%s.log' % i)
            if not os.path.isfile(clog):
                continue
            for tr, _b, tp in _msg_log(clog):
                if t0 is not None and (tr is None or tr < t0):
                    continue
                if tr is None or tp is None or tp <= 0:
                    continue
                lats.append((tr - tp) * 1e3)
        media = statistics.mean(lats) if lats else None
        csv_media = r.get('app_lat_media_global_ms', '')
        print('  c%-3s run=%-6s n=%4d global=%-8s csv_media=%s'
              % (carga, run, len(lats),
                 '%.2f' % media if media is not None else 'None', csv_media))
