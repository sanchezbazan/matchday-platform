#!/usr/bin/env bash
# Build the lambda package: handler.py + libraries compiled for lambda (arm64, Python 3.14).
set -euo pipefail

cd "$(dirname "$0")"
rm -rf build
mkdir build

pip install \
    --target build \
    --platform manylinux_2_28_aarch64 \
    --implementation cp \
    --python-version 3.14 \
    --only-binary=:all: \
    -r requirements.txt

cp handler.py build/
echo "Built $(du -sh build | cut -f1) in services/ingestion/build/"
