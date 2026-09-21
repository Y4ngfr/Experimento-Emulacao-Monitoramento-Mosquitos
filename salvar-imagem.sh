#!/usr/bin/env bash
# =============================================================================
# salvar-imagem.sh — publica a imagem local do experimento no registry remoto
# (Docker Hub). Rode NA MAQUINA LOCAL; o servidor usa 'docker pull' via up.sh.
#
#   bash salvar-imagem.sh                      -> publica yangfr10/mn-wifi:latest
#                                                e :<data> (ex.: 2026-09-17)
#   bash salvar-imagem.sh <registro/repo>      -> outro destino (privado, etc.)
#
# Requisito: docker login ao registry de antemao. Nao faz download nenhum.
# =============================================================================
set -euo pipefail

IMG_SRC=${IMG_SRC:-mn-wifi-containernet:latest}
REG="${1:-yangfr10/mn-wifi}"
DATE_TAG="$(date +%F)"

for tag in latest "$DATE_TAG"; do
  docker tag "$IMG_SRC" "$REG:$tag"
  echo "[salvar-imagem.sh] Publicando $REG:$tag ..."
  docker push "$REG:$tag"
done

echo "[salvar-imagem.sh] OK. No servidor:"
echo "  docker pull $REG:latest"
echo "  bash up.sh"