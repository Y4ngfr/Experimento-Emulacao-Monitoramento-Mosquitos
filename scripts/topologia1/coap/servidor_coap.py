#!/usr/bin/env python3
"""
Servidor CoAP do experimento — ramificação CoAP.

Substitui o par broker MQTT + gateway MQTT-SN (e o servidor_http): recebe os
metadados dos sensores via POST /meta (UDP/CoAP), persiste em JSONL e notifica
os cientistas via Observe (GET /stream), que é o análogo CoAP de assinar.

Uso:
  python3 servidor_coap.py --addr 0.0.0.0 --port 5683 --logdir /app/dados/coap
"""

import argparse
import asyncio
import datetime
import json
import logging
import os

import aiocoap
import aiocoap.resource as resource

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
LOG = logging.getLogger('servidor_coap')

STREAM_MAX = 64


class App:
    def __init__(self, meta_log):
        self.meta_log = meta_log
        self.stream = None
        self.recent = []
        self.stream_seq = 0
        self.msg_recv = 0
        self.bytes_recv = 0
        self.pub_sent = 0
        self.pub_bytes = 0

    def ingest(self, payload):
        texto = json.dumps(payload)
        n_bytes = len(texto.encode('utf-8'))
        self.stream_seq += 1
        item = {'stream_seq': self.stream_seq, 'meta': payload}
        self.recent.append(item)
        if len(self.recent) > STREAM_MAX:
            self.recent.pop(0)
        stamp = datetime.datetime.now().isoformat()
        line = '%s %s' % (stamp, texto)
        with open(self.meta_log, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        LOG.info('meta recebido (%d) de %s: %s', self.stream_seq,
                 payload.get('sensor', '?'), payload)
        n_obs = self.stream.n_observadores()
        self.msg_recv += 1
        self.bytes_recv += n_bytes
        self.pub_sent += n_obs
        self.pub_bytes += n_bytes * n_obs
        self.stream.updated_state()
        return self.stream_seq

    def snapshot(self):
        latest = self.recent[-1]['meta'] if self.recent else None
        return {'stream_seq': self.stream_seq, 'meta': latest}

    def stats(self):
        """Snapshot com contadores analogos ao $SYS do broker (GET /stats)."""
        n = self.stream.n_observadores() if self.stream else 0
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


class MetaResource(resource.Resource):
    def __init__(self, app):
        super().__init__()
        self.app = app

    async def render_post(self, request):
        try:
            payload = json.loads(request.payload.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            resp = aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                   payload=b'{"error":"bad json"}')
            return resp
        seq = self.app.ingest(payload)
        body = json.dumps({'ok': True, 'seq': seq}).encode('utf-8')
        return aiocoap.Message(code=aiocoap.CHANGED, payload=body)


class StreamResource(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.app = None

    def n_observadores(self):
        return len(getattr(self, '_observations', ()))

    async def render_get(self, request):
        body = json.dumps(self.app.snapshot()).encode('utf-8')
        return aiocoap.Message(payload=body)


class StatsResource(resource.Resource):
    def __init__(self, app):
        super().__init__()
        self.app = app

    async def render_get(self, request):
        body = json.dumps(self.app.stats()).encode('utf-8')
        return aiocoap.Message(payload=body)


class HealthResource(resource.Resource):
    async def render_get(self, request):
        return aiocoap.Message(payload=b'{"ok":true}')


def parse_args():
    p = argparse.ArgumentParser(description='Servidor CoAP dos metadados (srv1)')
    p.add_argument('--addr', default='0.0.0.0', help='Endereço de bind')
    p.add_argument('--port', type=int, default=5683, help='Porta UDP CoAP')
    p.add_argument('--logdir', default='/app/dados/coap', help='Diretório de dados')
    return p.parse_args()


async def run(args):
    os.makedirs(args.logdir, exist_ok=True)
    app = App(os.path.join(args.logdir, 'meta.log'))

    root = resource.Site()
    stream = StreamResource()
    stream.app = app
    app.stream = stream

    root.add_resource(('.well-known', 'core'),
                      resource.WKCResource(root.get_resources_as_linkheader))
    root.add_resource(('meta',), MetaResource(app))
    root.add_resource(('stream',), stream)
    root.add_resource(('stats',), StatsResource(app))
    root.add_resource(('health',), HealthResource())

    await aiocoap.Context.create_server_context(root, bind=(args.addr, args.port))
    LOG.info('servidor CoAP em %s:%d (POST /meta, GET /stream#observe)', args.addr, args.port)
    await asyncio.sleep(1e9)


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()