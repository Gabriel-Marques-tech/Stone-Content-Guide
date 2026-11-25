#!/usr/bin/env bash
# Repete a extração em rodadas até zerar a fila ou a cota diária acabar. Retomável.
cd "$(dirname "$0")/.." || exit 1
for _ in $(seq 1 30); do
  uv run python -u scripts/extrair.py > data/rodada.log 2>&1
  cat data/rodada.log >> data/extrair.log
  grep -qE 'ESGOTADA|; 0 na fila' data/rodada.log && break
  sleep 600
done
