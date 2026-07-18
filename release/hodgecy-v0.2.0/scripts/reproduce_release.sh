#!/usr/bin/env bash
set -euo pipefail

python scripts/validate_ckc_fixed_rational_batch.py
python scripts/build_ckc_239_240_241_theorem_values.py
python scripts/generate_paper_assets.py
python scripts/verify_smoothing_bridge_84_84a.py --force
python scripts/build_v0_2_0_release.py
python scripts/verify_v0_2_0_release.py
python -m pytest -q
