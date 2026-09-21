#!/bin/bash
# =============================================================================
# cleanup.sh — Limpeza completa do ambiente de emulação do Mininet-WiFi.
#
# Deve rodar DENTRO do container mininet-lab. Idempotente e tolerante a falhas
# (nunca quebra o container se algo não existir).
#
# O que isso resolve:
#   Cada run deixa estado residual (processos zumbis, bridges OVS, veths
#   órfãos, rádios hwsim sujos, socket do wmediumd). Rodar novamente sem limpar
#   "degrada" o ambiente: associação fica lenta/trava e os runs ficam mais
#   lentos até precisarem de um restart completo do container.
#
# Quando usar:
#   docker exec mininet-lab bash /app/scripts/topologia1/cleanup.sh
#
# Quando NÃO basta (o reset definitivo é reiniciar o container):
#   docker restart mininet-lab
# =============================================================================

# --- processos da pilha de emulação ----------------------------------------
pkill -9 -x ovs-controller 2>/dev/null
pkill -9 -x hostapd        2>/dev/null
pkill -9 -x wmediumd       2>/dev/null
pkill -9 -x mosquitto      2>/dev/null
pkill -9 -x bisquitt       2>/dev/null
pkill -9 -f 'mn_wifi/center' 2>/dev/null || true

# --- processos de aplicação (MQTT-SN / sensoriamento) -----------------------
# Zumbis das STAs/cientistas sobrevivem ao teardown da rede (nohup) e seguem
# escrevendo em logs / tentando publicar; matar aqui evita poluição e recuso.
pkill -9 -f 'sensor_pub.py'   2>/dev/null || true
pkill -9 -f 'cientista_sub.py' 2>/dev/null || true
pkill -9 -f 'coletor_no.py'  2>/dev/null || true
pkill -9 -f 'coletor_sys.py' 2>/dev/null || true

# --- processos da ramificação HTTP ------------------------------------------
pkill -9 -f 'servidor_http.py' 2>/dev/null || true
pkill -9 -f 'sensor_http.py'   2>/dev/null || true
pkill -9 -f 'cientista_stream.py' 2>/dev/null || true

# --- processos da ramificação CoAP ------------------------------------------
pkill -9 -f 'servidor_coap.py' 2>/dev/null || true
pkill -9 -f 'sensor_coap.py'   2>/dev/null || true
pkill -9 -f 'cientista_coap.py' 2>/dev/null || true

# --- bridges OVS dos APs e switch -------------------------------------------
for br in ap0 ap1 ap2 ap3 ap4 ap5 sw; do
    timeout 8 ovs-vsctl --if-exists del-br "$br" 2>/dev/null
done

# --- veths órfãos de runs interrompidos ------------------------------------
for i in 0 1 2 3 4 5; do ip link del ap${i}-eth0 2>/dev/null; done
for i in 0 1 2 3 4 5; do ip link del ap${i}-eth1 2>/dev/null; done
for i in 0 1 2 3 4 5 6; do ip link del gw-eth${i} 2>/dev/null; done
for i in 0 1 2 3 4 5; do ip link del sw-eth${i} 2>/dev/null; done
ip link del console-eth0 2>/dev/null

# --- rádios virtuais + socket do simulador de meio --------------------------
rmmod mac80211_hwsim 2>/dev/null
rm -f /var/run/wmediumd.sock
rm -f /tmp/mn*.apconf
rm -f /app/scripts/topologia1/*.apconf

true