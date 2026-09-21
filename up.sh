#!/usr/bin/env bash
# =============================================================================
# up.sh — sobe o container do experimento WSN-WiFi (mininet-wifi + containernet)
# com tudo o que ele precisa. Use no servidor remoto E na maquina local.
#
#   bash up.sh
#
# Fluxo:
#   1. garante a imagem do experimento puxando do REGISTRY REMOTO (Docker Hub):
#      IMG=yangfr10/mn-wifi:latest (so faz docker pull se ausente — localmente
#      ela ja esta em cache, entao nao ha download repetido); force a
#      atualizacao de uma versao nova com "UP_PULL=1 bash up.sh";
#   2. (re)cria o container mininet-lab: --privileged, tmpfs p/ o dataset,
#      volumes de scripts/config/dados, rede/pid host e X11 (se houver DISPLAY);
#   3. inicia openvswitch (+ tenta carregar mac80211_hwsim, best-effort) e
#      valida o ambiente (mosquitto + imports das libs do experimento).
#
# Para publicar uma versao nova da imagem: bash salvar-imagem.sh
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

IMG=${IMG:-yangfr10/mn-wifi:latest}
NAME=${NAME:-mininet-lab}
RAMFS_SIZE="${RAMFS_SIZE:-2G}"

# ---------------------------------------------------------------------
# 1. Garantir a imagem do experimento (puxa do registry remoto se faltar)
# ---------------------------------------------------------------------
if [ "${UP_PULL:-0}" = "1" ] || ! docker image inspect "$IMG" >/dev/null 2>&1; then
  echo "[up.sh] Obtendo $IMG do registry remoto..."
  if ! docker pull "$IMG"; then
    echo "[up.sh] ERRO: nao foi possivel baixar $IMG." >&2
    echo "        Verifique a rede e, se o registry for privado, se voce fez" >&2
    echo "        docker login antes. Corrija e rode 'bash up.sh' de novo." >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------
# 2. Volumes (criam os diretorios do host se ainda nao existirem)
# ---------------------------------------------------------------------
mkdir -p scripts config dados

# ---------------------------------------------------------------------
# 3. (Re)criar o container
# ---------------------------------------------------------------------
docker rm -f "$NAME" >/dev/null 2>&1 || true

DISPLAY_ARGS=()
if [ -n "${DISPLAY:-}" ]; then
  DISPLAY_ARGS=(-e DISPLAY="$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix)
fi

docker run -d \
  --privileged \
  --pid=host \
  --network=host \
  --tmpfs "/mnt/dataset-ram:size=${RAMFS_SIZE}" \
  --name "$NAME" \
  "${DISPLAY_ARGS[@]}" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /sys:/sys \
  -v /lib/modules:/lib/modules \
  -v "$PWD/scripts:/app/scripts" \
  -v "$PWD/config:/app/config" \
  -v "$PWD/dados:/app/dados" \
  "$IMG" \
  bash -c "service openvswitch-switch start; modprobe mac80211_hwsim 2>/dev/null || true; exec tail -f /dev/null"

# ---------------------------------------------------------------------
# 4. Validacao do ambiente dentro do container
# ---------------------------------------------------------------------
sleep 3
if [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != "true" ]; then
  echo "[up.sh] ERRO: container nao ficou no ar. Veja os logs:"
  docker logs "$NAME" || true
  exit 1
fi

docker exec "$NAME" bash -lc \
  'command -v mosquitto >/dev/null && python3 -c "import mininet, mn_wifi, paho.mqtt.client, aiocoap, tflite_runtime, numpy" && echo "[up.sh] ambiente OK dentro do container"'

echo
echo "[up.sh] Container '$NAME' pronto e rodando."
echo "  imagem       : $IMG"
echo "  atualizar    : UP_PULL=1 bash up.sh"
echo "  experimento  : docker exec $NAME python3 /app/scripts/topologia1/experimento.py --runs 15 --tempo 2100 --app mqtt"
echo "  shell        : docker exec -it $NAME bash"
echo "  resultados   : dados/experimentos (bind do host)"