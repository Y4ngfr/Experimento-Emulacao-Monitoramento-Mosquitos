#!/usr/bin/env python3
"""
experimento.py — Orquestrador de experimentos da topologia WSN-WiFi (MQTT).

Para cada CARGA de sensores (padrao p/ PC local ~6GB RAM: 10, 20, 30, 40, 50
— parametrizavel, ate 5 cargas) roda N runs de TEMPO segundos, deixando a rede, os sensores,
os coletores e os cientistas subirem e coletarem como em um experimento real.
Ao fim de cada run:

  1. arquiva os CSVs brutos (rede_no/ app/ sys/ mqtt logs) em
     <out>/experimento_<ts>/raw/c<CARGA>_run<K>/           (cada run tem ID unico);
  2. calcula um resumo numerico por run e o grava em
     <out>/experimento_<ts>/metricas_por_run.csv            (1 linha por run,
     com identificadores experimento/carga/run — pronto para media por carga
     ou analise por run em cima do CSV).

Uso (DENTRO do container):
  docker exec mininet-lab python3 /app/scripts/topologia1/experimento.py \
      --runs 3 --tempo 300

Parametros:
  --runs            Quantidade de runs por carga (default 3)
  --tempo           Duracao de coleta de cada run em segundos (default 300)
  --warmup          Periodo de estabilizacao em segundos (default 0). Com o
                    sistema COMPLETO rodando (sensores, cientistas e coletores),
                    aguarda --warmup s e entao descarta, na analise, toda
                    amostra/mensagem com timestamp anterior a esse instante —
                    a janela medida corresponde exatamente a --tempo.
  --sensores_por_ap Sensores associados a cada AP (default 10 -> n_aps = carga/10)
  --cargas          Cargas de sensores a rodar, separadas por virgula
                    (default "10,20,30,40,50"; maximo 5 escolhas)
  --app             Protocolo de aplicacao: mqtt | http | coap (default mqtt)
  --out             Diretorio base de resultados (default /app/dados/experimentos)

Parametros de rede/topologia (repassados ao topologia.py):
  --channel         Canal Wi-Fi 802.11g 2.4GHz (default 3)
  --raio            Distancia maxima sensor->AP em m (default 60)
  --raio_min        Distancia minima sensor->AP em m (default 30)
  --dist_aps        Distancia entre APs no grid em m (default 150)
  --systemloss      Perda de sistema (fator; 1 = 0 dB, valor do experimento)
  --exploss         Expoente de perda logNormalShadowing (default 2.0)
  --variance        Variância (sigma) do sombreamento log-normal (default 4.0)

Interno (para smoke tests):
  env EXP_CARGAS="10,15" limita as cargas testadas quando --cargas nao e dado.
"""

import argparse
import csv
import datetime
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

BASE = '/app/scripts/topologia1'
METRIC_DIR = '/app/dados/metricas'
MQTT_DIR = '/app/dados/mqtt'

APP_DATA = {
    'mqtt': '/app/dados/mqtt',
    'http': '/app/dados/http',
    'coap': '/app/dados/coap',
}

CARGAS = [10, 20, 30, 40, 50]           # hardcoded (cargas p/ PC local, ~6GB RAM)
APPS_CIENT = ('1', '2', '3')
GRACE = 540                                # margem (s) p/ boot + teardown usada apenas
                                          # na estimativa de tempo total do experimento


def log(msg):
    line = '[%s] %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line, flush=True)
    return line


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError('cmd falhou (%d): %s\n%s' % (r.returncode, cmd, r.stderr))
    return r


def mem_disponivel_mb():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) // 1024
    return None


def num(v):
    try:
        if v is None or str(v).strip() == '':
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def ler_csv(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def ler_t0(metric_dir):
    """Instante (epoch) em que a janela de medicao comecou, gravado pelo
    topologia.py quando --warmup>0; None se nao houve warmup (mede tudo)."""
    p = os.path.join(metric_dir, 't0')
    if not os.path.isfile(p):
        return None
    try:
        return float(open(p).read().strip())
    except (ValueError, OSError):
        return None


def filtrar_ts(rows, t0, col='ts'):
    """Retorna apenas linhas com ts >= t0 (janela de medicao). Sem t0, tudo."""
    if t0 is None:
        return rows
    out = []
    for r in rows:
        v = num(r.get(col))
        if v is not None and v >= t0:
            out.append(r)
    return out


def ultimo_primeiro(rows, col):
    """Total = ultimo - primeiro da coluna cumulativa."""
    vals = [num(r[col]) for r in rows]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    return vals[-1] - vals[0]


def soma_taxa(rows, col, interval=5.0):
    """Reconstroi o acumulado a partir das taxas por intervalo (rate*deltats)."""
    tot = 0.0
    prev_ts = None
    n_amostras = 0
    for r in rows:
        ts = num(r['ts'])
        v = num(r[col])
        if v is not None and ts is not None:
            if prev_ts is not None:
                tot += v * (ts - prev_ts)
                n_amostras += 1
            prev_ts = ts
    return tot if n_amostras else None


def media_col(rows, col):
    vals = [num(r[col]) for r in rows if num(r[col]) is not None]
    return statistics.mean(vals) if vals else None


def min_col(rows, col):
    vals = [num(r[col]) for r in rows]
    vals = [v for v in vals if v is not None]
    return min(vals) if vals else None


def max_col(rows, col):
    vals = [num(r[col]) for r in rows]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


def ultimo(rows, col):
    for r in reversed(rows):
        v = num(r[col])
        if v is not None:
            return v
    return None


def conv(v, fator):
    """Aplica fator de conversao de unidade em v (None-safe)."""
    return v * fator if v is not None else None


# --------------------------------------------------------------------------
# Parsing dos CSVs gerados pela run
# --------------------------------------------------------------------------

def rede_wifi_do_no(path, wifi_iface_sub, t0=None):
    """Metricas wifi de um no (agg sobre linhas do CSV da janela de medicao)."""
    if not os.path.isfile(path):
        return {}
    rows = [r for r in ler_csv(path) if 'wlan' in r.get('iface', '')]
    rows = filtrar_ts(rows, t0)
    if not rows:
        return {}
    out = {
        'pkts_tx': ultimo_primeiro(rows, 'tx_pkts'),
        'pkts_rx': ultimo_primeiro(rows, 'rx_pkts'),
        'bytes_tx': ultimo_primeiro(rows, 'tx_bytes'),
        'bytes_rx': ultimo_primeiro(rows, 'rx_bytes'),
        'retries': soma_taxa(rows, 'tx_retries_s'),
        'failed': soma_taxa(rows, 'tx_failed_s'),
        'beacon_loss': soma_taxa(rows, 'beacon_loss_s'),
        'peer_tx_pkts': ultimo_primeiro(rows, 'peer_tx_pkts'),
        'rssi': media_col(rows, 'rssi_dbm'),
        'bitrate': media_col(rows, 'tx_bitrate'),
    }
    return out


def status_falha(log_path):
    if not os.path.isfile(log_path):
        return None
    with open(log_path) as f:
        return sum(1 for line in f if 'FALHOU' in line)


def run_parsing(dd, status, log_path=None, t0=None):
    """Consolida metricas de um run a partir de dd (diretorio metricas).

    Se t0 (fim do warmup) for dado, toda linha com ts < t0 e descartada e os
    contadores cumulativos sao rebaseados no instante t0 — assim o warmup
    (sistema completo rodando) nao entra nas metricas.
    """
    m = {}
    m['status'] = status
    m['falhas_assoc'] = status_falha(log_path)

    # --- STAs (soma/agrega TODOS os sensores instrumentados) + AP -------------
    sta = {'pkts_tx': 0, 'pkts_rx': 0, 'bytes_tx': 0, 'bytes_rx': 0, 'retries': 0,
           'failed': 0, 'beacon_loss': 0, 'rssi': [], 'bitrate': []}
    sta_csvs = []
    rede_no = os.path.join(dd, 'rede_no')
    if os.path.isdir(rede_no):
        for nome in os.listdir(rede_no):
            if nome.startswith('sta') and nome.endswith('.csv'):
                idx = nome[3:-4]
                if idx.isdigit():
                    sta_csvs.append((int(idx), nome))
    sta_csvs.sort()
    for _, nome in sta_csvs:
        w = rede_wifi_do_no(os.path.join(rede_no, nome), 'wlan0', t0)
        for k in ('pkts_tx', 'pkts_rx', 'bytes_tx', 'bytes_rx', 'retries',
                  'failed', 'beacon_loss'):
            if w.get(k) is not None:
                sta[k] += w[k]
        if w.get('rssi') is not None:
            sta['rssi'].append(w['rssi'])
        if w.get('bitrate') is not None:
            sta['bitrate'].append(w['bitrate'])
    m['n_stas_csv'] = len(sta_csvs)
    m['sta_pkts_tx'], m['sta_pkts_rx'] = sta['pkts_tx'], sta['pkts_rx']
    m['sta_bytes_tx'], m['sta_bytes_rx'] = sta['bytes_tx'], sta['bytes_rx']
    m['sta_retries'], m['sta_failed'], m['sta_beacon_loss'] = (
        sta['retries'], sta['failed'], sta['beacon_loss'])
    m['sta_rssi_media_dbm'] = (statistics.mean(sta['rssi']) if sta['rssi'] else None)
    m['sta_bitrate_media_mbps'] = (statistics.mean(sta['bitrate']) if sta['bitrate'] else None)

    ap = rede_wifi_do_no(os.path.join(dd, 'rede_no', 'ap0.csv'), 'wlan1', t0)
    m['ap_pkts_tx'] = ap.get('pkts_tx')
    m['ap_pkts_rx'] = ap.get('pkts_rx')
    m['ap_retries'], m['ap_failed'], m['ap_beacon_loss'] = (
        ap.get('retries'), ap.get('failed'), ap.get('beacon_loss'))
    m['ap_peer_tx_pkts'] = ap.get('peer_tx_pkts')
    m['ap_rssi_media_dbm'] = ap.get('rssi')
    m['ap_bitrate_media_mbps'] = ap.get('bitrate')

    # --- broker ($SYS) ------------------------------------------------------
    bp = os.path.join(dd, 'sys', 'broker.csv')
    if os.path.isfile(bp):
        rows = filtrar_ts(ler_csv(bp), t0)
        if rows:
            if t0 is not None:
                # janela de medicao: contadores = ultimo - primeiro (baseline em t0)
                m['broker_msg_recv'] = ultimo_primeiro(rows, 'msg_recv')
                m['broker_msg_sent'] = ultimo_primeiro(rows, 'msg_sent')
                m['broker_pub_sent'] = ultimo_primeiro(rows, 'pub_sent')
            else:
                m['broker_msg_recv'] = ultimo(rows, 'msg_recv')
                m['broker_msg_sent'] = ultimo(rows, 'msg_sent')
                m['broker_pub_sent'] = ultimo(rows, 'pub_sent')
            m['broker_clients'] = max([r['clients'] for r in rows if num(r['clients']) is not None] or [None])
            m['broker_rx_kbps'] = conv(media_col(rows, 'brx_bps'), 1e-3)
            m['broker_tx_kbps'] = conv(media_col(rows, 'btx_bps'), 1e-3)

    # --- aplicacao (cientistas) ---------------------------------------------
    c = {'msgs': [], 'gaps': 0, 'dups': 0, 'goodput': [], 'perda': [],
         'lat_med': [], 'lat_min': [], 'lat_max': [], 'lat_p99': []}
    n_app = 0
    for i in APPS_CIENT:
        p = os.path.join(dd, 'app', '%s.csv' % i)
        if not os.path.isfile(p):
            p = os.path.join(dd, 'app', 'cient%s.csv' % i)
            if not os.path.isfile(p):
                continue
        rows = filtrar_ts(ler_csv(p), t0)
        if not rows:
            continue
        n_app += 1
        if t0 is not None:
            # cumulativos: rebaseia na 1a amostra da janela (>= t0)
            b_msgs = num(rows[0].get('msgs')) or 0
            b_gaps = num(rows[0].get('gaps')) or 0
            b_dups = num(rows[0].get('dups')) or 0
        else:
            b_msgs = b_gaps = b_dups = 0
        msgs_w = (ultimo(rows, 'msgs') or 0) - b_msgs
        gaps_w = (ultimo(rows, 'gaps') or 0) - b_gaps
        dups_w = (ultimo(rows, 'dups') or 0) - b_dups
        c['msgs'].append(msgs_w)
        c['gaps'] += gaps_w
        c['dups'] += dups_w
        g = media_col(rows, 'goodput_bps')
        if g is not None:
            c['goodput'].append(g)
        if t0 is not None:
            c['perda'].append(100.0 * gaps_w / max(1, msgs_w))
        else:
            pp = ultimo(rows, 'perda_app_%')
            if pp is not None:
                c['perda'].append(pp)
        ml = media_col(rows, 'lat_media_us')
        if ml is not None:
            c['lat_med'].append(ml)
        mx = max_col(rows, 'lat_max_us')
        if mx is not None:
            c['lat_max'].append(mx)
        mn = min_col(rows, 'lat_min_us')
        if mn is not None:
            c['lat_min'].append(mn)
        p99 = media_col(rows, 'lat_p99_us')
        if p99 is not None:
            c['lat_p99'].append(p99)
    m['n_app_csv'] = n_app
    m['app_msgs_total'] = sum(c['msgs'])
    m['app_goodput_media_kbps'] = conv(statistics.mean(c['goodput']) if c['goodput'] else None, 1e-3)
    m['app_perda_pct'] = (statistics.mean(c['perda']) if c['perda'] else None)
    m['app_gaps'] = c['gaps']
    m['app_dups'] = c['dups']
    m['app_lat_media_ms'] = conv(statistics.mean(c['lat_med']) if c['lat_med'] else None, 1e-3)
    m['app_lat_min_ms'] = conv(min(c['lat_min']) if c['lat_min'] else None, 1e-3)
    m['app_lat_max_ms'] = conv(max(c['lat_max']) if c['lat_max'] else None, 1e-3)
    m['app_lat_p99_ms'] = conv(statistics.mean(c['lat_p99']) if c['lat_p99'] else None, 1e-3)
    return m


# --------------------------------------------------------------------------
# Metricas de deteccao / accuracy (metadados dos sensores)
# --------------------------------------------------------------------------

NOME_PARA_CLASSE = {
    'aedes_aegypti_macho': 0,
    'aedes_aegypti_femea': 1,
    'outros_mosquitos': 2,
    'ambiente': 3,
}

CLASSES = [0, 1, 2, 3]


def _ts_prefix(line, i_json):
    """Epoch do timestamp ISO que prefixa a linha (posicao do primeiro '{')."""
    try:
        prefix = line[:i_json].split(' [')[0].strip()
        return datetime.datetime.fromisoformat(prefix).timestamp()
    except (ValueError, IndexError):
        return None


def _extrair_metas_de_log(path, t0=None):
    """Le um arquivo de log e retorna lista de dicts de metadados.

    Com t0 (fim do warmup), descarta linhas gravadas antes de t0.
    """
    metas = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            i = line.find('{')
            if i < 0:
                continue
            if t0 is not None:
                t_linha = _ts_prefix(line, i)
                if t_linha is not None and t_linha < t0:
                    continue
            try:
                meta = json.loads(line[i:])
            except ValueError:
                continue
            if 'classe_real' not in meta or 'sensor' not in meta:
                continue
            metas.append(meta)
    return metas


def _predita_para_indice(meta):
    """Extrai o indice da classe predita a partir do metadado."""
    c = meta.get('classe')
    if isinstance(c, int) or (isinstance(c, str) and c.isdigit()):
        return int(c)
    if c in NOME_PARA_CLASSE:
        return NOME_PARA_CLASSE[c]
    if 'probs' in meta and meta['probs']:
        return int(max(range(len(meta['probs'])),
                       key=lambda k: meta['probs'][k]))
    return None


def metricas_deteccao(app_dir, t0=None):
    """Le meta.log e/ou cient*.log de um diretorio e retorna dict com metricas."""
    candidatos = []
    meta_log = os.path.join(app_dir, 'meta.log')
    if os.path.isfile(meta_log):
        candidatos.append(meta_log)
    for i in APPS_CIENT:
        p = os.path.join(app_dir, 'cient%s.log' % i)
        if os.path.isfile(p):
            candidatos.append(p)
    if not candidatos:
        return {}

    vistos = set()
    metas = []
    for path in sorted(candidatos):
        for meta in _extrair_metas_de_log(path, t0):
            chave = (meta.get('sensor'), meta.get('seq'))
            if chave in vistos:
                continue
            vistos.add(chave)
            pred = _predita_para_indice(meta)
            real = meta.get('classe_real')
            if real is None or pred is None:
                continue
            ok = bool(meta.get('correto', pred == real))
            metas.append({'real': real, 'pred': pred, 'ok': ok})

    total = len(metas)
    if total == 0:
        return {}

    ok_total = sum(1 for m in metas if m['ok'])
    m_out = {
        'det_n_total': total,
        'det_corretas': ok_total,
        'det_acuracia_pct': round(100.0 * ok_total / total, 2),
    }

    for c in CLASSES:
        sub = [m for m in metas if m['real'] == c]
        n = len(sub)
        ok = sum(1 for m in sub if m['ok'])
        m_out['det_classe_%d_obs' % c] = n
        m_out['det_classe_%d_ok' % c] = ok
        m_out['det_classe_%d_taxa_pct' % c] = round(100.0 * ok / n, 2) if n else None

    return m_out


def _msg_log(path):
    """Gera (ts_recepcao, payload_bytes, ts_pub) de cada msg de um cient*.log."""
    saida = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            i = line.find('{')
            if i < 0:
                continue
            payload = line[i:].strip()
            try:
                meta = json.loads(payload)
            except ValueError:
                continue
            ts_pub = meta.get('ts')
            ts_recv = None
            try:
                ts_recv = datetime.datetime.fromisoformat(line[:i].split(' [')[0]).timestamp()
            except (ValueError, IndexError):
                ts_recv = None
            saida.append((ts_recv, len(payload.encode('utf-8')),
                          ts_pub if isinstance(ts_pub, (int, float)) else None))
    return saida


def _percentil(vals_sorted, p):
    """Percentil p (0-100) de uma lista ja ordenada (interpolacao linear)."""
    if not vals_sorted:
        return None
    k = (len(vals_sorted) - 1) * p / 100.0
    lo = min(int(k), len(vals_sorted) - 1)
    hi = min(lo + 1, len(vals_sorted) - 1)
    return vals_sorted[lo] + (vals_sorted[hi] - vals_sorted[lo]) * (k - lo)


def metricas_app_log(app_dir, t0=None):
    """Goodput SUSTENTADO e latencia robusta a partir dos cient*.log.

    Corrige a metrica por-janela de metricas_app.py, que e enviesada quando os
    sensores publicam em rajadas sincronizadas (media das taxas instantaneas
    superestima o throughput). Aqui:
      - goodput = soma dos payloads x 8 / (ultima - primeira entrega), por
        cientista, depois media entre os cientistas;
      - latencia = percentis p50/p90/p99 sobre TODAS as mensagens.

    Com t0 (fim do warmup), mensagens entregues antes de t0 sao descartadas.
    """
    gps, lats = [], []
    for i in APPS_CIENT:
        path = os.path.join(app_dir, 'cient%s.log' % i)
        if not os.path.isfile(path):
            continue
        msgs = [m for m in _msg_log(path)
                if t0 is None or (m[0] is not None and m[0] >= t0)]
        if not msgs:
            continue
        bytes_tot = sum(m[1] for m in msgs)
        t_recv = [m[0] for m in msgs if m[0] is not None]
        if bytes_tot and len(t_recv) >= 2 and t_recv[-1] > t_recv[0]:
            dur = t_recv[-1] - t_recv[0]
            gps.append(bytes_tot * 8.0 / 1000.0 / dur)
        lats.extend((m[0] - m[2]) * 1e3 for m in msgs
                    if m[0] is not None and m[2] is not None and m[2] > 0)
    out = {}
    if gps:
        out['app_goodput_sustentado_kbps'] = round(statistics.mean(gps), 4)
    if lats:
        lats.sort()
        out['app_lat_p50_ms'] = round(_percentil(lats, 50), 4)
        out['app_lat_p90_ms'] = round(_percentil(lats, 90), 4)
        out['app_lat_p99_ms_all'] = round(_percentil(lats, 99), 4)
    return out


# --------------------------------------------------------------------------
# Orquestracao
# --------------------------------------------------------------------------

def limpar_ambiente():
    sh('cd %s && bash cleanup.sh >/dev/null 2>&1' % BASE, check=False)
    time.sleep(2)


def reset_metricas(data_dir):
    shutil.rmtree(METRIC_DIR, ignore_errors=True)
    os.makedirs(os.path.join(METRIC_DIR, 'rede_no'))
    os.makedirs(os.path.join(METRIC_DIR, 'app'))
    os.makedirs(os.path.join(METRIC_DIR, 'sys'))
    os.makedirs(data_dir, exist_ok=True)
    for i in APPS_CIENT:
        open(os.path.join(data_dir, 'cient%s.log' % i), 'w').close()


def ultima_fase(log_path):
    """Ultima fase '*** ...' registrada no log da topologia (None se ainda nao
    ha marcador). Rele o arquivo inteiro a cada chamada: e pequeno e barato."""
    fase = None
    if not os.path.isfile(log_path):
        return None
    try:
        with open(log_path, encoding='utf-8', errors='replace') as f:
            for lin in f:
                lin = lin.strip()
                if lin.startswith('*** '):
                    fase = lin[4:]
                elif lin.startswith('***'):
                    fase = lin[3:]
                elif lin.startswith('TOPOLOGIA PRONTA'):
                    fase = 'TOPOLOGIA PRONTA'
    except OSError:
        return None
    return fase


def fmt_min(s):
    """Formata segundos de forma curta (ex.: 3m20s)."""
    s = int(max(0, s))
    return '%ds' % s if s < 120 else '%dm%02ds' % (s // 60, s % 60)


def roda_run(carga, run_id, tempo, n_aps, out_raw, app='mqtt', net=None, warmup=0,
             max_falhas_assoc=0, assoc_retries=3):
    """Roda uma carga/run, arquiva brutos e retorna dict de metricas.

    Se a associacao dos sensores falhar alem de --max-falhas-assoc, o
    topologia.py aborta com rc=3 ANTES de iniciar o cenario (nenhuma medicao).
    Aqui a run e repetida ate --assoc-retries e, so entao, registrada como
    falha — nunca roda a coleta com carga parcial silenciosa.
    """
    net = net or {}
    data_dir = APP_DATA[app]
    inicio = time.time()
    limpar_ambiente()
    mem_antes = mem_disponivel_mb()
    if mem_antes is not None and mem_antes < 900:
        log('    [AVISO] pouca RAM livre (%.0f MB) — run pode falhar' % mem_antes)

    log_arquivo = os.path.join(out_raw, 'topologia.log')

    def exec_tentativa():
        reset_metricas(data_dir)
        extra = ' '.join('--%s %g' % (k, v) for k, v in sorted(net.items()))
        cmd = ('cd %s && python3 topologia.py --n_sensores %d --n_aps %d '
               '--duracao %d --warmup %d --app %s --max-falhas-assoc %d %s </dev/null'
               % (BASE, carga, n_aps, tempo, warmup, app, max_falhas_assoc, extra))
        t_ini = time.time()
        with open(log_arquivo, 'w') as lf:
            p = subprocess.Popen(cmd, shell=True, start_new_session=True,
                                 stdout=lf, stderr=subprocess.STDOUT)
            fase_mostrada = None
            ultimo_tick = t_ini
            while p.poll() is None:
                time.sleep(5)
                fase = ultima_fase(log_arquivo)
                if fase is not None and fase != fase_mostrada:
                    fase_mostrada = fase
                    log('    [%s] %s' % (run_id, fase))
                agora = time.time()
                if agora - ultimo_tick >= 300:
                    ultimo_tick = agora
                    decorrido = agora - t_ini
                    coleta_fim = warmup + tempo - decorrido
                    log('    [%s] %s decorridos; coleta termina em ~%s'
                        % (run_id, fmt_min(decorrido), fmt_min(coleta_fim)))
            p.wait()
        return p

    p = None
    rc = None
    for tentativa in range(1, assoc_retries + 1):
        p = exec_tentativa()
        rc = p.returncode
        if rc == 3 and tentativa < assoc_retries:
            shutil.copy2(log_arquivo,
                         os.path.join(out_raw, 'topologia_tentativa%d.log' % tentativa))
            log('    [AVISO] %s: associacao incompleta (rc=3); '
                'retentando (%d/%d)...' % (run_id, tentativa + 1, assoc_retries))
            limpar_ambiente()
            continue
        break

    if p is None:
        status = 'assoc_falha(rc=3)'
    elif rc == 3:
        status = 'assoc_falha(rc=3)'
    elif rc != 0:
        status = 'falha(rc=%d)' % rc
    else:
        status = 'ok'

    t0 = ler_t0(METRIC_DIR)

    # arquivar metricas + logs do protocolo
    if os.path.isdir(METRIC_DIR):
        shutil.copytree(METRIC_DIR, os.path.join(out_raw, 'metricas'))
    data_arc = os.path.join(out_raw, app)
    os.makedirs(data_arc, exist_ok=True)
    for i in APPS_CIENT:
        src = os.path.join(data_dir, 'cient%s.log' % i)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(data_arc, 'cient%s.log' % i))
    meta_log = os.path.join(data_dir, 'meta.log')
    if os.path.isfile(meta_log):
        shutil.copy2(meta_log, os.path.join(data_arc, 'meta.log'))

    m = run_parsing(METRIC_DIR, status, log_arquivo, t0)
    m.update(metricas_deteccao(data_arc, t0))
    m.update(metricas_app_log(data_arc, t0))
    m['inicio_ts'] = int(inicio)
    m['fim_ts'] = int(time.time())
    m['wall_s'] = round(time.time() - inicio, 1)
    m['t0_ts'] = t0
    m['mem_antes_mb'] = mem_antes
    limpar_ambiente()
    log('    [FIM] status=%s wall=%.0fs rc=%s' % (status, m['wall_s'], rc))
    return m


def main():
    ap = argparse.ArgumentParser(description='Orquestrador de experimentos WSN-WiFi')
    ap.add_argument('--runs', type=int, default=3, help='Runs por carga (default 3)')
    ap.add_argument('--tempo', type=int, default=300, help='Duracao de coleta por run em s (default 300)')
    ap.add_argument('--warmup', type=int, default=0,
                    help='Estabilizacao em s com sistema completo rodando; os '
                         'primeiros N s sao descartados na analise (default 0)')
    ap.add_argument('--sensores_por_ap', type=int, default=10,
                    help='Sensores por AP (default 10 -> n_aps = carga/10)')
    ap.add_argument('--cargas', default=None,
                    help='Cargas de sensores, separadas por virgula '
                         '(default "10,20,30,40,50"; maximo 5 escolhas)')
    ap.add_argument('--app', choices=['mqtt', 'http', 'coap'], default='mqtt',
                    help='Protocolo de aplicacao (default mqtt)')
    ap.add_argument('--assoc-retries', type=int, default=3,
                    help='Repeticoes da run quando a associacao wifi falha (rc=3) '
                         'antes de registrar a run como assoc_falha (default 3)')
    ap.add_argument('--max-falhas-assoc', type=int, default=0,
                    help='Numero maximo de sensores que podem falhar a associacao '
                         'antes de abortar a run SEM iniciar a coleta (default 0 = rigido)')
    ap.add_argument('--out', default='/app/dados/experimentos', help='Base de resultados')

    ap.add_argument('--channel', type=int, default=3, help='Canal Wi-Fi 802.11g 2.4GHz (default 3)')
    ap.add_argument('--raio', type=float, default=60, help='Distancia maxima sensor->AP em m (default 60)')
    ap.add_argument('--raio_min', type=float, default=30, help='Distancia minima sensor->AP em m (default 30)')
    ap.add_argument('--dist_aps', type=float, default=150, help='Distancia entre APs em m (default 150)')
    ap.add_argument('--systemloss', type=float, default=1.0,
                    help='Perda de sistema, fator (1 = 0 dB; default 1.0)')
    ap.add_argument('--exploss', type=float, default=2.0, help='Expoente de perda logNormalShadowing (default 2.0)')
    ap.add_argument('--variance', type=float, default=4.0, help='Variância do sombreamento log-normal (default 4.0)')
    args = ap.parse_args()

    cargas = list(CARGAS)
    if args.cargas:
        cargas = [int(x) for x in args.cargas.split(',') if x.strip()]
    elif os.environ.get('EXP_CARGAS'):
        cargas = [int(x) for x in os.environ['EXP_CARGAS'].split(',') if x.strip()]

    cargas = sorted(set(cargas))
    if not cargas:
        ap.error('informe pelo menos uma carga (ex.: --cargas 10,15,20,25,30)')
    if len(cargas) > 5:
        ap.error('maximo de 5 cargas (recebidas %d)' % len(cargas))
    if any(c < 1 for c in cargas):
        ap.error('cargas devem ser numeros inteiros positivos')
    if args.sensores_por_ap < 1:
        ap.error('--sensores_por_ap deve ser >= 1')
    for c in cargas:
        if c % args.sensores_por_ap != 0:
            log('[AVISO] carga %d nao e multipla de --sensores_por_ap %d; '
                'distribuicao irregular' % (c, args.sensores_por_ap))

    if args.warmup < 0:
        ap.error('--warmup deve ser >= 0')
    if args.assoc_retries < 1:
        ap.error('--assoc-retries deve ser >= 1')
    if args.max_falhas_assoc < 0:
        ap.error('--max-falhas-assoc deve ser >= 0')

    net_args = {
        'channel': args.channel,
        'systemloss': args.systemloss,
        'exploss': args.exploss,
        'variance': args.variance,
        'raio': args.raio,
        'raio_min': args.raio_min,
        'dist_aps': args.dist_aps,
    }
    aps_por_carga = [max(1, c // args.sensores_por_ap) for c in cargas]

    os.makedirs(args.out, exist_ok=True)
    exp_id = 'experimento_%s' % time.strftime('%Y%m%d_%H%M%S')
    exp_dir = os.path.join(args.out, exp_id)
    raw_root = os.path.join(exp_dir, 'raw')
    os.makedirs(raw_root, exist_ok=True)

    lf = open(os.path.join(exp_dir, 'experimento.log'), 'w')
    def elog(msg):
        lf.write((msg if msg.endswith('\n') else msg + '\n'))
        lf.flush()

    elog(log('=== EXPERIMENTO %s ===' % exp_id))
    elog(log('Cargas: %s (APs: %s) | runs/carga: %d | tempo/run: %ds | warmup: %ds | protocolo: %s'
             % (cargas, aps_por_carga, args.runs, args.tempo, args.warmup, args.app)))
    elog(log('Associacao: max_falhas=%d | retries=%d'
             % (args.max_falhas_assoc, args.assoc_retries)))
    elog(log('Rede: raio=%gm raio_min=%gm dist_aps=%gm canal=%d sysloss=%g exp=%g var=%g'
             % (args.raio, args.raio_min, args.dist_aps, args.channel,
                args.systemloss, args.exploss, args.variance)))
    total_min = 0  # noqa (mantido para referencia)
    estimado = len(cargas) * args.runs * (args.warmup + args.tempo + GRACE) / 60
    elog(log('Tempo estimado total: ~%.0f min' % estimado))

    colunas = None
    for carga in cargas:
        n_aps_run = max(1, carga // args.sensores_por_ap)
        elog(log('=== CARGA %d sensores (%d APs) ===' % (carga, n_aps_run)))
        for run in range(1, args.runs + 1):
            run_id = 'c%d_run%d' % (carga, run)
            elog(log('  run %d/%d (carga %d) comecando: coleta %ds%s'
                     % (run, args.runs, carga, args.tempo,
                        ' + warmup %ds' % args.warmup if args.warmup else '')))
            out_raw = os.path.join(raw_root, run_id)
            os.makedirs(out_raw, exist_ok=True)
            try:
                m = roda_run(carga, run, args.tempo, n_aps_run, out_raw, args.app, net_args,
                     args.warmup, args.max_falhas_assoc, args.assoc_retries)
            except Exception as e:
                elog(log('  [ERRO] run %s falhou: %s' % (run_id, e)))
                m = {'status': 'erro_orquestrador', 'falhas_assoc': None,
                     'inicio_ts': int(time.time()), 'fim_ts': int(time.time()),
                     'wall_s': 0, 'mem_antes_mb': None}
            m['experimento'] = exp_id
            m['protocolo'] = args.app
            m['carga'] = carga
            m['run'] = run
            m['n_aps'] = n_aps_run
            m['sensores_por_ap'] = args.sensores_por_ap
            m['tempo_s'] = args.tempo
            m['warmup_s'] = args.warmup
            m['raio_m'] = args.raio
            m['raio_min_m'] = args.raio_min
            m['dist_aps_m'] = args.dist_aps
            m['channel'] = args.channel
            m['arquivo'] = out_raw

            csv_path = os.path.join(exp_dir, 'metricas_por_run.csv')
            novo_arquivo = not os.path.isfile(csv_path)
            with open(csv_path, 'a', newline='') as f:
                w = csv.writer(f)
                if novo_arquivo:
                    w.writerow(sorted(m.keys()))
                    colunas = sorted(m.keys())
                w.writerow([m.get(k) for k in (colunas or sorted(m.keys()))])
            elog(log('  [OK] %s -> %s' % (run_id, csv_path)))

    elog(log('=== EXPERIMENTO %s CONCLUIDO ===' % exp_id))
    elog(log('Resultados em: %s' % exp_dir))
    lf.close()


if __name__ == '__main__':
    main()