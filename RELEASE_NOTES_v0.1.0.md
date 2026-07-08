# HodgeCY v0.1.0

This release supports the first HodgeCY paper: "HodgeCY: Computational Hodge Atom Profiles and Smoothing Bridges for Double Octic Calabi--Yau Threefolds."

## Scientific status

- Arrangements 84 and 84a are recorded as degree112_certified.
- Exact G1/G2 genericity verification is repo-backed over Q for Q0 = x^4 + 2y^4 + 3z^4 + 5t^4 + xyzt and epsilon = 1.
- A characteristic-zero degree-112 saturated Jacobian certificate is repo-backed.
- ordinary_node_verified is not claimed.
- defect_verified is not claimed.
- Reducedness, Hessian-rank, critical-degree, Hilbert-function, defect, and operator validations remain pending.

## Included assets

- Cynk--Meyer data loaders and HodgeCY profile constructors.
- Smoothing-bridge verification artifacts.
- p4-collinearity graph assets for arrangements 84 and 84a.
- Smoothing-bridge table and generated figures.
- Reviewer-V4 audit certificate summaries.
- Tests enforcing status nonpromotion.

## Reproducibility

Commands:

python scripts/generate_paper_assets.py
python scripts/verify_smoothing_bridge_84_84a.py --force
python -m pytest -q
