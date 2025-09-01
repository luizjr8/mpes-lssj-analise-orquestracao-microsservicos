#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <script.js> [...]"
    exit 1
fi

for file in "$@"; do
    FILENAME=$(date +%Y%m%d_%H%M%S)
    name=$(basename "$file" .js)
    # cid é o $file sem extensao e sem k6-
    cid="${name#k6-}" 

    mkdir -p results
    echo "Running ${name}_${FILENAME}"
    echo "Container ID: $cid"   
    
    metrics="results/${name}_${FILENAME}_docker.jsonl"

    {
        while true; do
            ts=$(date --iso-8601=ns)
            docker stats --no-stream --format '{{json .}}' "$cid" \
              | jq --arg ts "$ts" '. + {timestamp:$ts}' >> "$metrics"
            sleep 1
        done
    } &
    stats_pid=$!
    echo "Stats PID: $stats_pid"

    k6 run \
      --out csv="results/${name}_${FILENAME}_metrics.csv" \
      --out json="results/${name}_${FILENAME}_metrics.json" \
      --summary-export "results/${name}_${FILENAME}_summary.json" \
      --summary-mode full \
      "$file"

    kill $stats_pid
    wait $stats_pid 2>/dev/null || true

    # Ler o docker.jsonl e gerar json com o sumário (max, min, avg, p90, p95)
    echo "Generating docker summary"    

    jq -s '
      map(
        .CPUPerc |= (sub("%$";"") | tonumber)
        | .MemUsage |= (
            capture("(?<val>[0-9.]+)(?<unit>MiB|GiB)") as $m
            | ($m.val|tonumber) * (if $m.unit=="GiB" then 1024 else 1 end)
          )
      )
      | {
          cpu: {
            max: (max_by(.CPUPerc).CPUPerc),
            min: (min_by(.CPUPerc).CPUPerc),
            avg: (map(.CPUPerc) | add / length),
            p90: (map(.CPUPerc) | sort | .[(length*0.90|floor)]),
            p95: (map(.CPUPerc) | sort | .[(length*0.95|floor)])
          },
          mem_mb: {
            max: (max_by(.MemUsage).MemUsage),
            min: (min_by(.MemUsage).MemUsage),
            avg: (map(.MemUsage) | add / length),
            p90: (map(.MemUsage) | sort | .[(length*0.90|floor)]),
            p95: (map(.MemUsage) | sort | .[(length*0.95|floor)])
          }
        }
    ' "$metrics" > "results/${name}_${FILENAME}_docker_summary.json"

done
