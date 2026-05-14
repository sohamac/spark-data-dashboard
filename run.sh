#!/bin/bash
# ──────────────────────────────────────────────────────────────────
#  Spark Data Dashboard — Startup Script
#  Usage:  bash run.sh
# ──────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use Java 11 (required — PySpark 3.5.x is incompatible with Java 21+)
JAVA11_HOME="/Library/Java/JavaVirtualMachines/temurin-11.jdk/Contents/Home"

if [ ! -d "$JAVA11_HOME" ]; then
  echo "❌  Java 11 not found at $JAVA11_HOME"
  echo "   Install it from: https://adoptium.net/"
  exit 1
fi

export JAVA_HOME="$JAVA11_HOME"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║      ⚡ Spark Data Dashboard  v1.0           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Java:   $(${JAVA_HOME}/bin/java -version 2>&1 | head -1)"
echo "Python: $(python3 --version)"
echo ""
echo "Starting server → http://localhost:8050"
echo ""

python3 app.py
