#!/bin/sh
set -eu

# npm/optional-dependency resolution can miss the platform-specific rollup binary
# in mounted node_modules volumes. Recover automatically before starting Vite.
if ! node -e "require('@rollup/rollup-linux-arm64-gnu')" >/dev/null 2>&1; then
  echo "Missing @rollup/rollup-linux-arm64-gnu, installing optional deps..."
  npm install --include=optional --no-audit --no-fund
fi

exec npm run dev
