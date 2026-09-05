#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"
echo "=== Building Erutor Portable Distribution ==="

rm -rf build/ dist/
mkdir -p build/zipapp_staging dist/

# 1. Build standard wheel and sdist
python3 -m build

# 2. Extract wheel and bundle all pure-python dependencies
WHEEL=$(ls dist/*.whl | head -n 1)
pip install --target build/zipapp_staging "$WHEEL"

# 3. Create standalone zipapp executable
python3 -m zipapp build/zipapp_staging -m "erutor.cli:main" -o dist/erutor -p "/usr/bin/env python3"
chmod +x dist/erutor

# Cleanup temporary staging
rm -rf build/zipapp_staging

echo "=== Build Complete ==="
ls -lh dist/
