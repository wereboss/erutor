#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"
echo "=== Building Erutor Portable Distribution ==="

rm -rf build/ dist/
mkdir -p build/zipapp_staging dist/

# Detect Python / Pip
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
else
    PYTHON="python3"
    PIP="pip"
fi

# 1. Build standard wheel and sdist
$PYTHON -m build

# 2. Extract wheel and bundle all pure-python dependencies
WHEEL=$(ls dist/*.whl | head -n 1)
$PIP install --target build/zipapp_staging "$WHEEL"

# 3. Create standalone zipapp executable
$PYTHON -m zipapp build/zipapp_staging -m "erutor.cli:main" -o dist/erutor -p "/usr/bin/env python3"
chmod +x dist/erutor

# Cleanup temporary staging
rm -rf build/zipapp_staging

echo "=== Build Complete ==="
ls -lh dist/
