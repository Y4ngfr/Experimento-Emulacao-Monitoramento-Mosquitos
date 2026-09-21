#!/usr/bin/env python3
"""
Servidor HTTP do experimento — ramificação HTTP.

Substitui o papel de "broker MQTT + gateway MQTT-SN" da variante MQTT:
recebe os metadados dos sensores (POST /meta), persiste como JSONL em
/app/dados/http/meta.log e encaminha aos cientistas assinantes via long-poll
(GET /stream), que é o análogo HTTP de assinar um tópico.

Uso:
  python3 servidor_http.py --port 8000 --logdir /app/dados/http
"""

import argparse
import datetime
import json
import logging
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger('servidor_http')

POLL_SECS = 25
SUB_QUEUE_MAX = 128


class App:
    def __init__(self, meta_log):
        self.meta_log = meta_log
        self._subs = set()
        self._lock = threading.Lock()
        self._seq = 0
        self.msg_recv = 0
        self.bytes_recv = 0
        self.pub_sent = 0
        self.pub_bytes = 0

    def publish(self, payload):
        texto = json.dumps(payload)
        n_bytes = len(texto.encode('utf-8'))
        entregues = 0
        bytes_ent = 0
        with self._lock:
            self._seq += 1
            seq = self._seq
            for q in list(self._subs):
                try:
                    q.put_nowait(payload)
                    entregues += 1
                    bytes_ent += n_bytes
                except queue.Full:
                    pass
            self.msg_recv += 1
            self.bytes_recv += n_bytes
            self.pub_sent += entregues
            self.pub_bytes += bytes_ent
        stamp = datetime.datetime.now().isoformat()
        line = '%s %s' % (stamp, texto)
        with open(self.meta_log, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        LOG.info('meta recebido (%d) de %s: %s', seq, payload.get('sensor', '?'), payload)
        return seq

    def subscribe(self):
        q = queue.Queue(maxsize=SUB_QUEUE_MAX)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def stats(self):
        """Snapshot com contadores analogos ao $SYS do broker (GET /stats)."""
        with self._lock:
            n = len(self._subs)
            return {
                'msg_recv': self.msg_recv,
                'msg_sent': self.pub_sent,
                'pub_sent': self.pub_sent,
                'pub_bytes': self.pub_bytes,
                'bytes_recv': self.bytes_recv,
                'bytes_sent': self.pub_bytes,
                'clients': n,
                'subs': n,
            }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        app = self.server.app
        if self.path == '/health':
            self._json(200, {'ok': True})
            return
        if self.path == '/stats':
            self._json(200, app.stats())
            return
        if self.path == '/stream':
            q = app.subscribe()
            try:
                try:
                    payload = q.get(timeout=POLL_SECS)
                except queue.Empty:
                    self._json(200, [])
                    return
                self._json(200, [payload])
            finally:
                app.unsubscribe(q)
            return
        self._json(404, {'error': 'not found'})

    def do_POST(self):
        app = self.server.app
        if self.path != '/meta':
            self._json(404, {'error': 'not found'})
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, TypeError):
            self._json(400, {'error': 'bad json'})
            return
        seq = app.publish(payload)
        self._json(200, {'ok': True, 'seq': seq})


class Server(ThreadingHTTPServer):
    daemon_threads = True


def parse_args():
    p = argparse.ArgumentParser(description='Servidor HTTP dos metadados (srv1)')
    p.add_argument('--port', type=int, default=8000, help='Porta TCP do servidor')
    p.add_argument('--logdir', default='/app/dados/http', help='Diretório de dados')
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.logdir, exist_ok=True)
    meta_log = os.path.join(args.logdir, 'meta.log')
    server = Server(('0.0.0.0', args.port), Handler)
    server.app = App(meta_log)
    LOG.info('servidor HTTP em 0.0.0.0:%d (POST /meta, GET /stream)', args.port)
    server.serve_forever()


if __name__ == '__main__':
    main()