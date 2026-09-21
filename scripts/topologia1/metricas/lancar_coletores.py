#!/usr/bin/env python3
"""
Lancador compartilhado dos coletores de metricas de REDE por no.

Usa o mesmo coletor_no.py que a ramificacao MQTT, nos MESMOS diretorios
(/app/dados/metricas/rede_no/), para que o experimento.py e o
resumo_metricas.py funcionem identicos nas 3 ramificacoes.

Uso (dentro da topologia):
  from lancar_coletores import lancar_coletores_rede
  lancar_coletores_rede(net, metricdir='/app/dados/metricas', interval=5.0)
"""

import os

COLETOR_NO = '/app/scripts/topologia1/metricas/coletor_no.py'
COLETOR_SYS = '/app/scripts/topologia1/metricas/coletor_sys.py'


def _bg(node, cmd):
    node.cmd('nohup %s >/dev/null 2>&1 &' % cmd)


def lancar_coletores_rede(net, metricdir='/app/dados/metricas', interval=5.0,
                          sys_fonte=None):
    """Lanca o coletor_no.py em todos os nos (srv1, gw, APs, STAs, cientistas, console).

    Se sys_fonte e dado (flags do coletor_sys, ex.: '--modo http --url http://...'),
    tambem lanca o coletor do PROCESSO CENTRAL no srv1, gravando sys/broker.csv
    — identico para mqtt/http/coap (o CSV e o fluxo nao mudam entre protocolos).
    """
    os.makedirs(os.path.join(metricdir, 'rede_no'), exist_ok=True)
    os.makedirs(os.path.join(metricdir, 'app'), exist_ok=True)
    os.makedirs(os.path.join(metricdir, 'sys'), exist_ok=True)

    srv = net['srv1']
    _bg(srv, 'python3 %s --out=%s/rede_no/srv1.csv --interval=%s'
        % (COLETOR_NO, metricdir, interval))
    _bg(net['gw'], 'python3 %s --out=%s/rede_no/gw.csv --interval=%s'
        % (COLETOR_NO, metricdir, interval))

    aps = getattr(net, 'aps', [])
    stas = getattr(net, 'stations', [])
    for ap in aps:
        api = ap.name  # 'ap0', 'ap1', ...
        _bg(ap, 'python3 %s --out=%s/rede_no/ap%s.csv --interval=%s'
            % (COLETOR_NO, metricdir, api[2:], interval))
    for sta in stas:
        name = sta.name  # 'sta0', 'sta1', ...
        idx = name.replace('sta', '')
        _bg(sta, 'python3 %s --out=%s/rede_no/sta%s.csv --interval=%s'
            % (COLETOR_NO, metricdir, idx, interval))
    for i in (1, 2, 3):
        ct = net['cientista%d' % i]
        _bg(ct, 'python3 %s --out=%s/rede_no/cient%d.csv --interval=%s'
            % (COLETOR_NO, metricdir, i, interval))

    if 'console' in net:
        _bg(net['console'], 'python3 %s --out=%s/rede_no/console.csv --interval=%s'
            % (COLETOR_NO, metricdir, interval))

    if sys_fonte:
        _bg(srv, 'python3 %s %s --out=%s/sys/broker.csv --interval=%s'
            % (COLETOR_SYS, sys_fonte, metricdir, interval))