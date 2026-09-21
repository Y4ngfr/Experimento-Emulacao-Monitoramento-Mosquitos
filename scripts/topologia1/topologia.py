import os
import sys
import random
import math
import time
import argparse
from time import sleep

import http_scenario
import coap_scenario

from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP 
from mn_wifi.cli import CLI
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference
from mininet.log import setLogLevel, info

class WSN_WiFi_Topology:
    def __init__(self, 
                 n_sensores, n_APs, channel, 
                 APtxpower, sensortxpower, systemLoss, expLoss, 
                 variance, raio, duracao=300, warmup=0,
                 raio_min=15, dist_aps=250
                 ):
        
        self.net = Mininet_wifi(
            link=wmediumd,
            wmediumd_mode=interference,
            accessPoint=OVSKernelAP,    # define o default global para todos os APs 
            mode="g",      # 802.11g (aceita apenas 2.4GHz, melhor para sensores)
            channel=channel
        )

        self.n_sensores = n_sensores
        self.n_APs = n_APs
        self.channel = channel
        self.APtxpower = APtxpower
        self.sensortxpower = sensortxpower
        self.systemLoss = systemLoss
        self.expLoss = expLoss
        self.variance = variance
        self.raio = raio
        self.raio_min = raio_min
        self.dist_aps = dist_aps
        self.duracao = duracao
        self.warmup = warmup
        self.sensores_por_cluster = self.n_sensores // self.n_APs
        self.construir_nos()

    def construir_nos(self):
        info("*** Criando Servidor Central\n")
        self.net.addHost('srv1', ip='11.0.0.10/16')

        # gw e ap são hardwares diferentes no experimento
        info("*** Criando Gateway\n")
        self.net.addHost('gw')

        info("*** Criando Cientistas\n")
        self.net.addHost('cientista1', ip='11.0.1.20/24')
        self.net.addHost('cientista2', ip='11.0.1.21/24')
        self.net.addHost('cientista3', ip='11.0.1.22/24')

        # switch dos cientistas para o servidor
        self.net.addSwitch('sw', dpid='0000000000000001')

        # Nó console no netns do host com inNamespace=False para conectar ao Thingsboard
        info("*** Criando nó Console (netns do host, porta p/ ThingsBoard)\n")
        self.net.addHost('console', inNamespace=False, ip='12.10.0.2/24')

        APs_positions, sensors_positions = self.calcular_posicoes()
        ips_sensores = self.atribuir_ips()

        info("*** Criando Access Points (Clusters)\n")
        for i in range(self.n_APs) :
            self.net.addAccessPoint(
                f'ap{i}',
                ssid=f'cluster_{i}',
                mode='g',
                channel=self.channel,
                txpower=self.APtxpower, # dBm
                position=APs_positions[i]
            )

        info("*** Criando Sensores\n")
        for i in range(self.n_sensores) :
            j = min(i // self.sensores_por_cluster, self.n_APs - 1)

            self.net.addStation(
                f'sta{i}',
                ssid=f'cluster_{j}',
                mode='g',
                channel=self.channel,
                txpower=self.sensortxpower,
                ip = ips_sensores[i],
                position=sensors_positions[i]
            )

        self.net.setPropagationModel(model="logNormalShadowing", sL=self.systemLoss, exp=self.expLoss, variance=self.variance)

    def add_backhaul_links(self):
        "Links Ethernet do backhaul"
        info("*** Configurando Backhaul (Ethernet)\n")

        for i in range(self.n_APs):
            self.net.addLink(self.net['gw'], self.net[f'ap{i}']) # esse link resultará em na interface 'gw-ethi'

        self.net.addLink(self.net['srv1'], self.net['gw'])
        self.net.addLink(self.net['srv1'], self.net['sw'])
        self.net.addLink(self.net['srv1'], self.net['console'])

        self.net.addLink(self.net['sw'], self.net['cientista1'])
        self.net.addLink(self.net['sw'], self.net['cientista2'])
        self.net.addLink(self.net['sw'], self.net['cientista3'])

    def configurar_rede(self):
        gw = self.net['gw']
        # sw = self.net['sw']
        servidor = self.net['srv1']

        # Habilitar IP forwarding somente no gateway (APs não roteiam)
        gw.cmd('sysctl -w net.ipv4.ip_forward=1')

        # Interfaces do gateway para os sensores
        for i in range(self.n_APs):
            gw.cmd(f'ip addr add 10.{i}.0.1/16 dev gw-eth{i}')
            gw.cmd(f'ip neigh flush dev gw-eth{i}')
            info(f"rede gw gw-eth{i} -> 10.{i}.0.1/16 \n")

        gw.cmd(f'ip addr add 11.0.0.2/16 dev gw-eth{self.n_APs}') # interface do gw para o servidor 
        gw.cmd(f'ip neigh flush dev gw-eth{self.n_APs}')

        # Rota default do gw para o servidor
        gw.cmd('ip route add default via 11.0.0.10')

        # ===== srv1: rotas para os clusters via gw =====
        for i in range(self.n_APs):
            servidor.cmd(f'ip route add 10.{i}.0.0/16 via 11.0.0.2')

        # ===== APs: pontes L2 =====
        for i in range(self.n_APs):
            ap = self.net[f'ap{i}']
            bridge = f'ap{i}'
            radio = f'ap{i}-wlan1'
            ap.cmd(f'ovs-vsctl --if-exists del-port {bridge} {radio.replace("wlan1", "wlan2")}')
            if radio not in ap.cmd(f'ovs-vsctl list-ports {bridge}'):
                ap.cmd(f'ovs-vsctl add-port {bridge} {radio}')
                ap.cmd(f'ip link set {radio} up')
            ap.cmd(f'ip link set {bridge} up')
            ap.cmd(f'ovs-ofctl add-flow {bridge} "priority=0,actions=NORMAL"')

        # ===== Sensores: rota default via gw do cluster =====
        for i in range(self.n_sensores):
            cluster = min(i // self.sensores_por_cluster, self.n_APs - 1)
            sta = self.net[f'sta{i}']
            intf = sta.wintfs[0].name
            sta.cmd(f'ip route add default via 10.{cluster}.0.1 dev {intf}')
    
        # ===== Console ↔ srv1 =====
        servidor.cmd('ip addr add 12.10.0.1/24 dev srv1-eth2')
        servidor.cmd('ip link set srv1-eth2 up')
        servidor.cmd('ip route add 12.10.0.2/32 dev srv1-eth2')

        # ===== srv1 ↔ cientistas (switch) =====
        servidor.cmd('ip addr add 11.0.1.1/24 dev srv1-eth1')
        servidor.cmd('ip link set srv1-eth1 up')

        # ===== switch =====
        self.net['sw'].cmd('ovs-ofctl add-flow sw priority=0,actions=NORMAL')

        self.net['cientista1'].cmd('ip route add default via 11.0.1.1')
        self.net['cientista2'].cmd('ip route add default via 11.0.1.1')
        self.net['cientista3'].cmd('ip route add default via 11.0.1.1')

    def associar_wifi(self):
        """Associa sensores aos APs, com repassadas até estabilizar.

        Sob carga (>=100 STAs), o handshake de associacao (probe/auth/assoc)
        passa pelo wmediumd e pode demorar mais que a janela de espera para
        completar; na associacao one-shot isso deixava a STA offline o
        experimento inteiro. Aqui fazemos ate 3 passadas por STA (janela maior
        nas repassadas) para nao descartar associacoes apenas lentas por causa
        da fila/processamento do wmediumd.
        """
        info("*** Associando sensores aos APs (após hostapd)\n")

        def iface(i):
            return self.net[f'sta{i}'].wintfs[0].name

        def conectada(i):
            return 'Connected' in self.net[f'sta{i}'].cmd('iw dev %s link' % iface(i))

        def tenta(i, janela):
            cluster = min(i // self.sensores_por_cluster, self.n_APs - 1)
            intf = iface(i)
            self.net[f'sta{i}'].cmd(
                'sh -c "iw dev %s disconnect 2>/dev/null; '
                'timeout 10 iw dev %s connect cluster_%d 2>/dev/null"'
                % (intf, intf, cluster))
            for _ in range(janela):
                if conectada(i):
                    return True
                sleep(1)
            return False

        pendentes = list(range(self.n_sensores))
        sem_progresso = 0
        for volta in range(3):
            if not pendentes:
                break
            janela = 15 if volta == 0 else 25
            ordem = list(reversed(pendentes)) if volta else pendentes
            if volta:
                info("  ...repassada %d: %d STAs pendentes\n" % (volta + 1, len(pendentes)))
            novo = [i for i in ordem if not tenta(i, janela)]
            sem_progresso = sem_progresso + 1 if len(novo) == len(pendentes) else 0
            pendentes = novo
            if sem_progresso >= 2:
                break
        if pendentes:
            info("*** %d sensores FALHARAM a associacao apos 3 passadas\n" % len(pendentes))
            for i in sorted(pendentes):
                info("  %s FALHOU\n" % self.net[f'sta{i}'].name)
        return pendentes

    def calcular_posicoes(self):
        n_clusters = self.n_APs
        qtd_filas = math.ceil(n_clusters / 5)
        endereco_base = [100, 100, 15]

        APs_positions = [] 
        sensors_positions = []

        contador = 0

        for i in range(qtd_filas):
            for j in range(5):
                if contador >= self.n_APs:
                    break
                APs_positions.append((endereco_base[0] + (j)*self.dist_aps, endereco_base[1] + (i)*self.dist_aps, endereco_base[2])) 
                contador += 1

        for i in APs_positions:
            for j in range(self.sensores_por_cluster):
                # ponto aleatório na coroa com raio míninmo r_min e raio máximo r_max
                U = random.random()
                r_min = self.raio_min
                r_max = self.raio
                r = math.sqrt(r_min**2 + U * (r_max**2 - r_min**2))
                theta = random.uniform(0, 2 * math.pi)
                sensors_positions.append((i[0] + r * math.cos(theta), i[1] + r * math.sin(theta), endereco_base[2]))

        APs_positions = [f"{x},{y},{z}" for x, y, z in APs_positions]
        sensors_positions = [f"{x},{y},{z}" for x, y, z in sensors_positions]

        return APs_positions, sensors_positions

    def atribuir_ips(self):
        sensores_por_cluster = self.n_sensores // self.n_APs
        ips_sensores = []

        for i in range(self.n_sensores):
            cluster = i // sensores_por_cluster
            pos = i % sensores_por_cluster
        
            if pos < 255 * 246:
                sensor_high = pos // 246
                sensor_low = (pos % 246) + 10
            else:
                sensor_high = 255
                sensor_low = (pos - (255 * 246)) + 10

            # pula os 10 primeiros endereços em cada bloco
            # Cada bloco tem 246 endereços úteis (.10 a .255)
        
            ips_sensores.append(f'10.{cluster}.{sensor_high}.{sensor_low}/16')

        return ips_sensores

    def mqtt_scenario(self):
        mosquittoconf = '/app/scripts/topologia1/mqtt/mosquitto.conf'
        sensorpub = '/app/scripts/topologia1/mqtt/sensor_pub.py'
        cientistasub = '/app/scripts/topologia1/mqtt/cientista_sub.py'
        dataset_ram = '/mnt/dataset-ram'
        metricdir = '/app/dados/metricas'
        interval = 5.0

        from metricas import lancar_coletores
        self.garantir_dataset(dataset_ram)

        info('*** [MQTT] Iniciando broker mosquitto no srv1\n')
        srv = self.net['srv1']
        srv.cmd(f"mosquitto -c {mosquittoconf} -d")

        sleep(2) # espera o mosquitto subir

        srvip = srv.IP()

        info('*** [MQTT] Iniciando publicadores nos sensores\n')
        for i in range(self.n_sensores):
            cluster = min(i // self.sensores_por_cluster, self.n_APs - 1) + 1
            sta = self.net[f'sta{i}']
            sta.cmd(f"python3 {sensorpub} --srvip={srvip} --id={i} "
                    f"--cluster={cluster} --dataset={dataset_ram} "
                    f">/dev/null 2>&1 &")

        info('*** [MQTT] Iniciando assinantes nos cientistas\n')
        for i in (1, 2, 3):
            ct = self.net[f'cientista{i}']
            ct.cmd(f"mkdir -p /app/dados/mqtt; "
                   f"python3 {cientistasub} --broker={srvip} --id={i} "
                   f"--topic=meta/# --log=/app/dados/mqtt/cient{i}.log "
                   f"--metrics={metricdir}/app --window=20 "
                   f">/dev/null 2>&1 &")

        info('*** [MQTT] Iniciando coletores de metricas de rede\n')
        lancar_coletores.lancar_coletores_rede(self.net, metricdir, interval,
                                               sys_fonte='--modo mqtt --broker 127.0.0.1')

        self.iniciar_janela(metricdir)

        info('*** [MQTT] Coletando por %.0fs...\n' % self.duracao)
        sleep(self.duracao)

    def iniciar_janela(self, metricdir):
        """Se --warmup>0, aguarda o sistema completo estabilizar (warmup) e
        registra o instante t0 em metricas/t0. O parsing do experimento descarta
        toda amostra/mensagem com timestamp anterior a t0."""
        if self.warmup <= 0:
            return
        info('*** Warmup de %.0fs com sistema completo (cientistas + coletores '
             'rodando); os dados desse periodo serao descartados na analise\n'
             % self.warmup)
        sleep(self.warmup)
        os.makedirs(metricdir, exist_ok=True)
        with open(os.path.join(metricdir, 't0'), 'w') as f:
            f.write(str(time.time()))

    def http_scenario(self):
        dataset_ram = '/mnt/dataset-ram'
        metricdir = '/app/dados/metricas'
        interval = 5.0

        self.garantir_dataset(dataset_ram)
        import http_scenario
        http_scenario.iniciar(self.net, espera=self.duracao, n_aps=self.n_APs,
                              metricdir=metricdir, interval=interval,
                              warmup=self.warmup)

    def coap_scenario(self):
        dataset_ram = '/mnt/dataset-ram'
        metricdir = '/app/dados/metricas'
        interval = 5.0

        self.garantir_dataset(dataset_ram)
        import coap_scenario
        coap_scenario.iniciar(self.net, espera=self.duracao, n_aps=self.n_APs,
                              metricdir=metricdir, interval=interval,
                              warmup=self.warmup)

    def garantir_dataset(self, dataset_ram):
        """Garante o dataset nas .bin dentro da RAM (tmpfs)."""
        if os.path.isfile(os.path.join(dataset_ram, '0.bin')):
            return
        info('*** [MQTT] Carregando dataset na RAM (tmpfs)...\n')
        os.system('python3 /app/scripts/topologia1/carregar_dataset.py '
                  '--dest %s >/dev/null 2>&1' % dataset_ram)
        if not os.path.isfile(os.path.join(dataset_ram, '0.bin')):
            info('*** [MQTT] ERRO: tmpfs indisponivel em %s\n' % dataset_ram)
            sys.exit(1)

def run_topology():
    parser = argparse.ArgumentParser(description="Executar Topologia")
    parser.add_argument("--n_sensores", type=int, default=15, help="Define o número de sensores totais")
    parser.add_argument("--n_aps", type=int, default=3, help="Define o número de pontos de acesso totais")
    parser.add_argument("--channel", type=int, default=3, help="Define qual canal será utilizado pelos dispositivos")
    parser.add_argument("--aptxpower", type=float, default=15, help="Define a potência de transmissão dos pontos de acesso (em dBm)")
    parser.add_argument("--sensortxpower", type=float, default=30, help="Define a potência de transmissão dos sensores (em dBm)")
    parser.add_argument("--systemloss", type=float, default=3, help="Fator de perda de sistema do modelo de propagação (fator 1 = 0 dB; deve ser > 0)")
    parser.add_argument("--exploss", type=float, default=3, help="Parâmetro expoente de perda do modelo de perda (em dBm)")
    parser.add_argument("--variance", type=float, default=3, help="Parâmetro variância do modelo de perda (em dBm)")
    parser.add_argument("--raio", type=float, default=30, help="Raio de distância máximo dos sensores para o ponto de acesso (em metros)")
    parser.add_argument("--raio_min", type=float, default=15, help="Raio de distância mínimo dos sensores para o ponto de acesso (em metros)")
    parser.add_argument("--dist_aps", type=float, default=250, help="Distância entre pontos de acesso no grid (em metros)")
    parser.add_argument("--app", type=str, default="mqtt", help="Define o protocolo de aplicação (mqtt, http ou coap)")
    parser.add_argument("--duracao", type=int, default=300, help="Duração do experimento em segundos (tempo de coleta)")
    parser.add_argument("--warmup", type=int, default=0, help="Estabilização em segundos com o sistema completo rodando; os primeiros N s são descartados na análise (default 0)")
    parser.add_argument("--max-falhas-assoc", type=int, default=0,
                        help="Falhas de associacao toleradas antes de abortar a run "
                             "via exit(3) sem iniciar o cenario (default 0 = rigido)")

    args = parser.parse_args()

    if args.systemloss <= 0:
        parser.error('--systemloss deve ser > 0 (o modelo logNormalShadowing calcula '
                     '10*log10(4*pi*L); fator 1 = 0 dB)')

    if args.warmup < 0:
        parser.error('--warmup deve ser >= 0')

    n_sensores = args.n_sensores
    n_APs = args.n_aps
    channel = args.channel
    APtxpower = args.aptxpower
    sensortxpower = args.sensortxpower
    systemLoss = args.systemloss
    expLoss = args.exploss
    variance = args.variance
    raio = args.raio
    raio_min = args.raio_min
    dist_aps = args.dist_aps
    app = args.app

    topologia = WSN_WiFi_Topology(
        n_sensores=n_sensores, n_APs=n_APs, channel=channel,
        APtxpower=APtxpower, sensortxpower=sensortxpower, systemLoss=systemLoss, expLoss=expLoss,
        variance=variance, raio=raio, duracao=args.duracao, warmup=args.warmup,
        raio_min=raio_min, dist_aps=dist_aps
    )

    topologia.add_backhaul_links()

    topologia.net.configureNodes()

    info("*** Iniciando rede...\n")
    topologia.net.build()
    topologia.net.start()

    # ========== ASSOCIAR SENSORES (pós-start, hostapd no ar) ==========
    info("*** Aguardando hostapd...\n")
    sleep(5)
    faltantes = topologia.associar_wifi()

    if int(os.environ.get('EXP_FORCA_ASSOC_RC', '0')):
        info("*** [TESTE] EXP_FORCA_ASSOC_RC=1: simulando falha de associacao\n")
        faltantes = list(range(min(topologia.n_sensores, 3)))

    if len(faltantes) > args.max_falhas_assoc:
        sys.stderr.write('*** ABORTANDO RUN: %d sensores nao associaram (max permitido=%d); '
                         'nenhuma medicao iniciada\n'
                         % (len(faltantes), args.max_falhas_assoc))
        info('*** ABORTANDO RUN: %d sensores nao associaram (max permitido=%d); '
             'nenhuma medicao iniciada\n' % (len(faltantes), args.max_falhas_assoc))
        sys.exit(3)

    # ========== ROTEAMENTO (pós-start) ==========
    info("*** Configurando roteamento...\n")
    topologia.configurar_rede()

    if app == "mqtt":
        info("***MQTT\n")
        topologia.mqtt_scenario()
    elif app == "http":
        info("***HTTP\n")
        topologia.http_scenario()
    elif app == "coap":
        info("***CoAP\n")
        topologia.coap_scenario()
    else:
        info("***Protocolo %s nao suportado (mqtt|http|coap)\n" % app)
        exit(1)

    info("*** Cenário %s finalizado\n" % app)

    print("TOPOLOGIA PRONTA")
    CLI(topologia.net)

if __name__ == '__main__':
    setLogLevel('info')

    info("="*60 + "\n")
    info("Monitoramento WSN WiFi\n")
    info("="*60 + "\n")
    
    run_topology()