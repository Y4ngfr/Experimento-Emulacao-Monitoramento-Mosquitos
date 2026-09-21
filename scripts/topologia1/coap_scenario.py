#!/usr/bin/env python3
"""
Cenario CoAP para a topologia de monitoramento de mosquitos — ramificacao CoAP.

Mesmo fluxo da ramificacao MQTT, mudando apenas o transporte: os sensores
leem audio real do dataset na RAM, classificam na borda e enviam o METADADO via
CoAP POST /meta (UDP) ao servidor_coap em srv1:5683; o servidor persiste em
JSONL e notifica os cientistas via Observe (GET /stream). Coletores de metricas
de rede e de aplicacao rodam nos MESMOS diretorios da ramificacao MQTT.

Variavel de ambiente:
  COAP_NON=1  faz os sensores publicarem com mensagens nao confirmaveis (NON).
"""

import os
import time as time_mod

from mininet.log import info

BASE = '/app/scripts/topologia1'
COAP_DIR = '/app/dados/coap'
SENSOR_PY = os.path.join(BASE, 'coap', 'sensor_coap.py')
SERVER_PY = os.path.join(BASE, 'coap', 'servidor_coap.py')
CIENTISTA_PY = os.path.join(BASE, 'coap', 'cientista_coap.py')

USE_NON = os.environ.get('COAP_NON', '0') == '1'


def _cluster(i, n_sensores, n_aps):
    spc = max(1, n_sensores // n_aps)
    return min(i // spc, n_aps - 1) + 1


def _background(node, cmd, logfile):
    node.cmd('mkdir -p %s' % COAP_DIR)
    node.cmd('nohup %s >%s 2>&1 &' % (cmd, logfile))


def _limpar_dados():
    os.system('mkdir -p %s' % COAP_DIR)
    for name in ('meta.log', 'cient1.log', 'cient2.log', 'cient3.log'):
        open(os.path.join(COAP_DIR, name), 'w').close()


def _start_servidor(net, port):
    info('*** [CoAP] Iniciando servidor CoAP (srv1:%d)\n' % port)
    _background(
        net['srv1'],
        "python3 %s --port %d --logdir %s" % (SERVER_PY, port, COAP_DIR),
        os.path.join(COAP_DIR, 'servidor-coap.out'))


def _start_subscribers(net, stream_url, metricdir):
    info('*** [CoAP] Iniciando cientistas (Observe /stream: cient1..3)\n')
    for i in range(1, 4):
        node = net['cientista%d' % i]
        _background(
            node,
            "python3 %s --url %s --id cient%d --log %s --metrics %s --window 20" % (
                CIENTISTA_PY, stream_url, i,
                os.path.join(COAP_DIR, 'cient%d.log' % i),
                os.path.join(metricdir, 'app')),
            os.path.join(COAP_DIR, 'cient%d.out' % i))


def _start_sensors(net, meta_url, n_aps):
    modo = 'NON' if USE_NON else 'CON'
    ativos = sorted(int(n.name[3:]) for n in net.stations)
    n_sensores = len(ativos)
    info('*** [CoAP] Iniciando sensores via CoAP [%s] (sta%s)\n' %
         (modo, ','.join(str(i) for i in ativos)))
    for i in ativos:
        node = net['sta%d' % i]
        extra = ' --non' if USE_NON else ''
        _background(
            node,
            "python3 %s --url %s --id %d --cluster %d%s" % (
                SENSOR_PY, meta_url, i, _cluster(i, n_sensores, n_aps),
                extra),
            os.path.join(COAP_DIR, 'sta%d-coap.log' % i))


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
    info('CENARIO CoAP (%s)\n' % ('NON' if USE_NON else 'CON'))
    info('=' * 60 + '\n')

    srvip = net['srv1'].IP()
    port = 5683
    meta_url = 'coap://%s:%d/meta' % (srvip, port)
    stream_url = 'coap://%s:%d/stream' % (srvip, port)
    n_aps = n_aps if n_aps else max(1, len(getattr(net, 'aps', [])))

    _limpar_dados()
    _start_servidor(net, port)
    time_mod.sleep(2)

    _start_subscribers(net, stream_url, metricdir)
    _start_sensors(net, meta_url, n_aps)

    from metricas import lancar_coletores
    lancar_coletores.lancar_coletores_rede(
        net, metricdir, interval,
        sys_fonte='--modo coap --url coap://127.0.0.1:%d/stats' % port)

    if warmup and warmup > 0:
        info('*** [CoAP] Warmup de %.0fs com sistema completo (cientistas + '
             'coletores rodando); dados desse periodo serao descartados na '
             'analise\n' % warmup)
        time_mod.sleep(warmup)
        _registrar_t0(metricdir)

    info('*** [CoAP] Coletando por %.0fs...\n' % espera)
    time_mod.sleep(espera)

    info('=' * 60 + '\n')
    info('ESTADO DO CENARIO (apos %.0fs de coleta, warmup=%ds)\n' %
         (espera, warmup))
    info('=' * 60 + '\n')
    info('  Servidor  : POST %s | Observe %s\n' % (meta_url, stream_url))
    for i in range(1, 4):
        info('  cient%d recebeu %d metadados (Observe /stream)\n' %
             (i, _contar_log(os.path.join(COAP_DIR, 'cient%d.log' % i))))
    for i in sorted(int(n.name[3:]) for n in net.stations):
        info('  sta%-2d ciclos de sensoriamento: %d\n' %
             (i, _contar_log(os.path.join(COAP_DIR, 'sta%d-coap.log' % i))))
    info('  servidor : %d linhas em %s/meta.log\n' %
         (_contar_log(os.path.join(COAP_DIR, 'meta.log')), COAP_DIR))
    info('- Logs: %s (bind do host em dados/coap)\n' % COAP_DIR)
    info('=' * 60 + '\n')