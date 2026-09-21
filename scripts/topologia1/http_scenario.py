#!/usr/bin/env python3
"""
Cenario HTTP para a topologia de monitoramento de mosquitos — ramificacao HTTP.

Mesmo fluxo da ramificacao MQTT, mudando apenas o transporte: os sensores
leem audio real do dataset na RAM, classificam na borda e enviam o METADADO via
HTTP POST (/meta) ao servidor_http em srv1:8000; o servidor persiste em JSONL e
encaminha aos cientistas via long-poll (GET /stream). Os coletores de metricas
de rede (coletor_no.py) e as metricas de aplicacao dos cientistas
(metricas_app.py) rodam nos MESMOS diretorios da ramificacao MQTT, para que o
experimento.py / resumo_metricas.py funcionem identicos.
"""

import os
import time as time_mod

from mininet.log import info

BASE = '/app/scripts/topologia1'
HTTP_DIR = '/app/dados/http'
SENSOR_PY = os.path.join(BASE, 'http', 'sensor_http.py')
SERVER_PY = os.path.join(BASE, 'http', 'servidor_http.py')
CIENTISTA_PY = os.path.join(BASE, 'http', 'cientista_stream.py')


def _cluster(i, n_sensores, n_aps):
    spc = max(1, n_sensores // n_aps)
    return min(i // spc, n_aps - 1) + 1


def _background(node, cmd, logfile):
    node.cmd('mkdir -p %s' % HTTP_DIR)
    node.cmd('nohup %s >%s 2>&1 &' % (cmd, logfile))


def _limpar_dados():
    os.system('mkdir -p %s' % HTTP_DIR)
    for name in ('meta.log', 'cient1.log', 'cient2.log', 'cient3.log'):
        open(os.path.join(HTTP_DIR, name), 'w').close()


def _start_servidor(net, port):
    info('*** [HTTP] Iniciando servidor HTTP (srv1:%d)\n' % port)
    _background(
        net['srv1'],
        "python3 %s --port %d --logdir %s" % (SERVER_PY, port, HTTP_DIR),
        os.path.join(HTTP_DIR, 'httpd.out'))


def _start_subscribers(net, stream_url, metricdir):
    info('*** [HTTP] Iniciando cientistas (long-poll /stream: cient1..3)\n')
    for i in range(1, 4):
        node = net['cientista%d' % i]
        _background(
            node,
            "python3 %s --url %s --id cient%d --log %s --metrics %s --window 20" % (
                CIENTISTA_PY, stream_url, i,
                os.path.join(HTTP_DIR, 'cient%d.log' % i),
                os.path.join(metricdir, 'app')),
            os.path.join(HTTP_DIR, 'cient%d.out' % i))


def _start_sensors(net, meta_url, n_aps):
    ativos = sorted(int(n.name[3:]) for n in net.stations)
    n_sensores = len(ativos)
    info('*** [HTTP] Iniciando sensores via HTTP (sta%s)\n' %
         ','.join(str(i) for i in ativos))
    for i in ativos:
        node = net['sta%d' % i]
        _background(
            node,
            "python3 %s --url %s --id %d --cluster %d" %
            (SENSOR_PY, meta_url, i, _cluster(i, n_sensores, n_aps)),
            os.path.join(HTTP_DIR, 'sta%d-http.log' % i))


def _contar_log(path):
    if not os.path.exists(path):
        return 0
    with open(path, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)


def _registrar_t0(metricdir):
    """Se warmup>0, registra em metricas/t0 o fim do warmup (instante em que a
    janela de medicao comeca). O parsing descarta tudo com ts anterior a t0."""
    import time as _t
    os.makedirs(metricdir, exist_ok=True)
    with open(os.path.join(metricdir, 't0'), 'w') as f:
        f.write(str(_t.time()))


def iniciar(net, espera=300, n_aps=None, metricdir='/app/dados/metricas',
            interval=5.0, warmup=0):
    info('=' * 60 + '\n')
    info('CENARIO HTTP (sensor -> servidor -> cientistas)\n')
    info('=' * 60 + '\n')

    srvip = net['srv1'].IP()
    port = 8000
    meta_url = 'http://%s:%d/meta' % (srvip, port)
    stream_url = 'http://%s:%d/stream' % (srvip, port)
    n_aps = n_aps if n_aps else max(1, len(getattr(net, 'aps', [])))

    _limpar_dados()
    _start_servidor(net, port)
    time_mod.sleep(2)

    _start_subscribers(net, stream_url, metricdir)
    _start_sensors(net, meta_url, n_aps)

    from metricas import lancar_coletores
    lancar_coletores.lancar_coletores_rede(
        net, metricdir, interval,
        sys_fonte='--modo http --url http://127.0.0.1:%d/stats' % port)

    if warmup and warmup > 0:
        info('*** [HTTP] Warmup de %.0fs com sistema completo (cientistas + '
             'coletores rodando); dados desse periodo serao descartados na '
             'analise\n' % warmup)
        time_mod.sleep(warmup)
        _registrar_t0(metricdir)

    info('*** [HTTP] Coletando por %.0fs...\n' % espera)
    time_mod.sleep(espera)

    info('=' * 60 + '\n')
    info('ESTADO DO CENARIO (apos %.0fs de coleta, warmup=%ds)\n' %
         (espera, warmup))
    info('=' * 60 + '\n')
    info('  Servidor  : POST %s | stream %s\n' % (meta_url, stream_url))
    for i in range(1, 4):
        info('  cient%d recebeu %d metadados (long-poll /stream)\n' %
             (i, _contar_log(os.path.join(HTTP_DIR, 'cient%d.log' % i))))
    for i in sorted(int(n.name[3:]) for n in net.stations):
        info('  sta%-2d ciclos de sensoriamento: %d\n' %
             (i, _contar_log(os.path.join(HTTP_DIR, 'sta%d-http.log' % i))))
    info('  servidor : %d linhas em %s/meta.log\n' %
         (_contar_log(os.path.join(HTTP_DIR, 'meta.log')), HTTP_DIR))
    info('- Logs: %s (bind do host em dados/http)\n' % HTTP_DIR)
    info('=' * 60 + '\n')