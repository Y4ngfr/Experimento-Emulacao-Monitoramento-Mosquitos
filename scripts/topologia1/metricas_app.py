#!/usr/bin/env python3
"""
Motor de metricas de aplicacao COMPARTILHADO pelos cientistas das 3
ramificacoes (MQTT/HTTP/CoAP).

Alem do log cru das mensagens, mantem estado e grava um CSV de aplicacao com o
mesmo formato nas 3 ramificacoes (para comparacoes em cima do arquivo):

  ts, msgs, gaps, dups, goodput_bps, perda_app_%, lat_media_us,
  lat_min_us, lat_max_us, lat_p50_us, lat_p99_us

Metricas por linha (janela de --window mensagens):
  - latencia fim-a-fim = (recepcao - 'ts' embutido pelo sensor) em us;
  - goodput           = bytes de payload * 8 / tempo decorrido da janela;
  - perda aplicacao   = gaps acumulados no 'seq' por sensor / msgs;
  - duplicatas        = 'seq' repetido para o mesmo sensor.
"""

import csv
import datetime
import json
import os
import re
import statistics
import time

_TS_RE = re.compile(r'"ts":\s*([\d.eE+-]+)')

CSV_HEADER = ['ts', 'msgs', 'gaps', 'dups', 'goodput_bps', 'perda_app_%',
              'lat_media_us', 'lat_min_us', 'lat_max_us',
              'lat_p50_us', 'lat_p99_us']


class AppMetricas:
    def __init__(self, name, log, metrics_dir=None, window=20):
        self.name = name
        self.log = log
        self.window = window
        self.msgs = 0
        self.gaps = 0
        self.dups = 0
        self.bytes_in = 0
        self.lats = []
        self.last_seq = {}
        self.t0 = time.time()
        self.writer = None
        self.outf = None
        if metrics_dir:
            os.makedirs(metrics_dir, exist_ok=True)
            self.outf = open(os.path.join(metrics_dir, '%s.csv' % name),
                             'w', newline='')
            self.writer = csv.writer(self.outf)
            self.writer.writerow(CSV_HEADER)
            self.outf.flush()

    def registrar(self, payload, origem, agora=None):
        """Registra um metadado recebido.

        payload: texto JSON (ou dict) com 'ts' e 'seq' do sensor.
        origem : identificador da origem (topico MQTT ou sensor HTTP/CoAP).
        """
        agora = agora if agora is not None else time.time()
        text = payload if isinstance(payload, str) else json.dumps(payload)

        line = '%s [%s] recebido de %s: %s' % (
            datetime.datetime.fromtimestamp(agora).isoformat(),
            self.name, origem, text)
        print(line, flush=True)
        with open(self.log, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

        self.msgs += 1
        self.bytes_in += len(text.encode('utf-8'))

        m = _TS_RE.search(text)
        if not m:
            return
        try:
            ts_pub = float(m.group(1))
            seq = int(json.loads(text).get('seq', 0))
        except Exception:
            return

        lat = (agora - ts_pub) * 1e6  # microsegundos
        self.lats.append(lat)

        if origem in self.last_seq:
            delta = seq - self.last_seq[origem]
            if delta > 1:
                self.gaps += delta - 1
            elif delta == 0:
                self.dups += 1
        self.last_seq[origem] = seq

        if len(self.lats) >= self.window:
            self.flush()

    def flush(self):
        if not self.lats:
            return
        lats = self.lats
        self.lats = []
        now = time.time()
        dur = max(0.001, now - self.t0)
        self.t0 = now
        gbps = self.bytes_in * 8 / dur
        self.bytes_in = 0
        if self.writer is None:
            return
        row = [round(now, 3), self.msgs, self.gaps, self.dups,
               round(gbps),
               round(self.gaps / max(1, self.msgs) * 100, 2),
               round(statistics.mean(lats), 1), round(min(lats), 1),
               round(max(lats), 1), round(statistics.median(lats), 1),
               round(sorted(lats)[int(len(lats) * 0.99)] if len(lats) > 1 else lats[0], 1)]
        self.writer.writerow(row)
        self.outf.flush()

    def close(self):
        self.flush()
        if self.outf is not None:
            self.outf.close()