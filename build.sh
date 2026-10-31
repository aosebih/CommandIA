#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
