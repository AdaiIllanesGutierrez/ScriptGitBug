#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# --- Auto-fix: si Docker no responde por permisos, relanzar con el grupo activo ---
if ! docker info >/dev/null 2>&1; then
    echo "Docker sin permisos en esta sesión -- relanzando con el grupo docker activo..."
    exec sg docker -c "\"$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")\""
fi


cd "$BASE_DIR/gitbug-java"

poetry run python "$SCRIPT_DIR/run_screened_bugs.py" \
  --gitbug-repo "$BASE_DIR/gitbug-java" \
  --evosuite-jar "$BASE_DIR/evosuiteJUAMPI/master/target/evosuite-master-1.2.1-SNAPSHOT.jar" \
  --bugs-csv "$SCRIPT_DIR/bugs_java_assigned.csv" \
  --seeds 3147383999447 9617663486099 5379124608314 \
  --workers 6 --cleanup-targets \
  --limit 100 \
  --work-root "$BASE_DIR/resultados/JUAMPI" \

