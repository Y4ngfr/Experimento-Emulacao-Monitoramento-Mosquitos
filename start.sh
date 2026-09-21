#!/usr/bin/env bash
# start.sh — mantido por compatibilidade; delega toda a logica ao up.sh.
cd "$(dirname "$0")"
exec bash up.sh "$@"