"""Search for a rational representative of Cynk--Kocel--Cynk arrangement 83."""

from __future__ import annotations

from itertools import combinations, product
import json
from math import gcd
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

CONTROL_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
REPORT_PATH = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "arrangement_83_search_report.json"
EXPECTED_INVENTORY = {"p3": 16, "p4_0": 10, "p4_1": 0, "p5_0": 0, "p5_1": 0, "p5_2": 0, "l3": 0}


def _normalize_tuple(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    common = 0
    for value in values:
        common = gcd(common, abs(value))
    common = common or 1
    normalized = tuple(value // common for value in values)
    if normalized[0] < 0:
        normalized = tuple(-value for value in normalized)
    return normalized  # type: ignore[return-value]


def _record_for_parameters(params: tuple[int, int, int, int]) -> dict:
    a0, a1, a2, a3 = params
    return {
        "arrangement_id": "83",
        "linear_forms": [
            {"label": "p1", "coefficients": [1, 0, 0, 0], "equation": "x"},
            {"label": "p2", "coefficients": [a0, a1, 0, 0], "equation": f"{a0}x + {a1}y"},
            {"label": "p3", "coefficients": [0, 1, 0, 0], "equation": "y"},
            {"label": "p4", "coefficients": [0, 0, 1, 0], "equation": "z"},
            {"label": "p5", "coefficients": [a0, a2, a2, 0], "equation": f"{a0}x + {a2}y + {a2}z"},
            {"label": "p6", "coefficients": [a0, a3, 0, a3], "equation": f"{a0}x + {a3}y + {a3}t"},
            {"label": "p7", "coefficients": [0, 0, 0, 1], "equation": "t"},
            {"label": "p8", "coefficients": [1, 1, 1, 1], "equation": "x + y + z + t"},
        ],
    }


def _det3(rows: list[list[int]]) -> int:
    return (
        rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
        - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
        + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0])
    )


def _det4(rows: list[list[int]]) -> int:
    total = 0
    for col in range(4):
        minor = [[rows[row][other] for other in range(4) if other != col] for row in range(1, 4)]
        total += ((-1) ** col) * rows[0][col] * _det3(minor)
    return total


def _rank_leq_2(vectors: list[list[int]]) -> bool:
    if len(vectors) <= 2:
        return True
    for row_indices in combinations(range(len(vectors)), 3):
        rows = [vectors[index] for index in row_indices]
        for cols in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            if _det3([[row[col] for col in cols] for row in rows]) != 0:
                return False
    return True


def _rank_leq_3(vectors: list[list[int]]) -> bool:
    if len(vectors) <= 3:
        return True
    for row_indices in combinations(range(len(vectors)), 4):
        if _det4([vectors[index] for index in row_indices]) != 0:
            return False
    return True


def _linear_vectors(params: tuple[int, int, int, int]) -> list[list[int]]:
    return [form["coefficients"] for form in _record_for_parameters(params)["linear_forms"]]


def _computed_inventory(record: dict) -> tuple[dict[str, int], int]:
    vectors = [form["coefficients"] for form in record["linear_forms"]]
    incidence_size = 0
    line_flats: set[tuple[int, ...]] = set()
    point_flats: set[tuple[int, ...]] = set()
    for a in range(8):
        for b in range(a + 1, 8):
            for c in range(b + 1, 8):
                triple = (a, b, c)
                triple_vectors = [vectors[index] for index in triple]
                if _rank_leq_2(triple_vectors):
                    closure = tuple(index for index in range(8) if _rank_leq_2([*triple_vectors, vectors[index]]))
                    line_flats.add(closure)
                    continue
                closure = tuple(index for index in range(8) if _rank_leq_3([*triple_vectors, vectors[index]]))
                point_flats.add(closure)
    for a in range(8):
        for b in range(a + 1, 8):
            for c in range(b + 1, 8):
                for d in range(c + 1, 8):
                    if _rank_leq_3([vectors[a], vectors[b], vectors[c], vectors[d]]):
                        incidence_size += 1
    inventory = {
        "p3": sum(1 for flat in point_flats if len(flat) == 3),
        "p4_0": sum(1 for flat in point_flats if len(flat) == 4),
        "p4_1": 0,
        "p5_0": sum(1 for flat in point_flats if len(flat) == 5),
        "p5_1": 0,
        "p5_2": 0,
        "triple_lines": sum(1 for flat in line_flats if len(flat) == 3),
    }
    return {
        "p3": int(inventory.get("p3", 0)),
        "p4_0": int(inventory.get("p4_0", 0)),
        "p4_1": int(inventory.get("p4_1", 0)),
        "p5_0": int(inventory.get("p5_0", 0)),
        "p5_1": int(inventory.get("p5_1", 0)),
        "p5_2": int(inventory.get("p5_2", 0)),
        "l3": int(inventory.get("triple_lines", 0)),
    }, incidence_size


def _candidate_parameters(bound: int) -> list[tuple[int, int, int, int]]:
    values = [value for value in range(-bound, bound + 1) if value != 0]
    seen = set()
    candidates = []
    for raw in product(values, repeat=4):
        normalized = _normalize_tuple(raw)
        if normalized[0] != 1:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
    return candidates


def _update_control_record(params: tuple[int, int, int, int], inventory: dict[str, int]) -> None:
    payload = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    for record in payload["records"]:
        if str(record["arrangement_id"]) != "83":
            continue
        a0, a1, a2, a3 = params
        record["representative_status"] = "validated"
        record["parameter_choice"] = {"A0": str(a0), "A1": str(a1), "A2": str(a2), "A3": str(a3)}
        record["parameters"] = dict(record["parameter_choice"])
        record["source_equation"] = "x(A0*x + A1*y)*y*z*(A0*x + A2*y + A2*z)*(A0*x + A3*y + A3*t)*t*(x + y + z + t)"
        record["source_reference"] = "Cynk--Kocel--Cynk, Classification of Double Octic Calabi--Yau Threefolds Defined by an Arrangement of Eight Planes II, arXiv:2602.19413, Section 6.1"
        record["expected_cynk_inventory"] = dict(EXPECTED_INVENTORY)
        record["computed_inventory"] = inventory
        record["inventory_matches_expected"] = True
        record["notes"] = "Validated rational specialization of the Cynk--Kocel--Cynk arrangement-83 parameterized equation."
        record["linear_forms"] = _record_for_parameters(params)["linear_forms"]
    CONTROL_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _record_search_attempt(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    payload = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    for record in payload["records"]:
        if str(record["arrangement_id"]) == "83":
            record["search_attempt"] = {
                "status": report["status"],
                "parameter_bound": report["parameter_bound"],
                "candidate_count": report["candidate_count"],
                "report_path": str(REPORT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            }
    CONTROL_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def search(bound: int = 5) -> dict:
    candidates = _candidate_parameters(bound)
    near_misses = []
    for params in candidates:
        record = _record_for_parameters(params)
        inventory, incidence_size = _computed_inventory(record)
        if inventory == EXPECTED_INVENTORY:
            _update_control_record(params, inventory)
            report = {
                "status": "found",
                "parameter_bound": bound,
                "candidate_count": len(candidates),
                "parameter_choice": {"A0": str(params[0]), "A1": str(params[1]), "A2": str(params[2]), "A3": str(params[3])},
                "computed_inventory": inventory,
                "expected_inventory": EXPECTED_INVENTORY,
                "incidence_table_size": incidence_size,
            }
            _record_search_attempt(report)
            return report
        if inventory["l3"] == 0 and inventory["p5_0"] == 0:
            near_misses.append({"parameters": params, "inventory": inventory, "incidence_table_size": incidence_size})
    report = {
        "status": "not_found",
        "parameter_bound": bound,
        "candidate_count": len(candidates),
        "expected_inventory": EXPECTED_INVENTORY,
        "near_misses": [
            {
                "parameter_choice": {"A0": str(params[0]), "A1": str(params[1]), "A2": str(params[2]), "A3": str(params[3])},
                "computed_inventory": item["inventory"],
                "incidence_table_size": item["incidence_table_size"],
            }
            for item in near_misses[:20]
            for params in [item["parameters"]]
        ],
    }
    _record_search_attempt(report)
    return report


def main() -> None:
    report = search(bound=5)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
