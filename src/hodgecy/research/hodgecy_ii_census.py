"""Source-level HodgeCY II fidelity census helpers.

The helpers in this module classify already reconstructed source assemblies.
They intentionally do not promote raw CKC equation extraction records to
validated source complexes, and they do not make any node- or Hodge-atom
realization claim.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping


INVENTORY_KEYS = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")
HODGE_KEYS = ("h12", "h11", "euler")


def stable_fingerprint(kind: str, payload: Mapping[str, Any]) -> str:
    """Return a deterministic kind-qualified sha256 fingerprint."""

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{kind}:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def natural_arrangement_key(arrangement_id: str) -> tuple[int, str]:
    """Sort CKC labels numerically while keeping suffixes such as 84a stable."""

    digits = ""
    suffix = ""
    for char in str(arrangement_id):
        if char.isdigit() and not suffix:
            digits += char
        else:
            suffix += char
    return (int(digits or 0), suffix)


def inventory_tuple(inventory: Mapping[str, Any]) -> tuple[int, ...]:
    """Return the canonical seven-entry source-local inventory tuple."""

    return tuple(int(inventory.get(key, 0) or 0) for key in INVENTORY_KEYS)


def hodge_tuple(hodge: Mapping[str, Any] | None) -> tuple[int, ...] | None:
    """Return the canonical Hodge triple if it is available."""

    if not hodge:
        return None
    try:
        return tuple(int(hodge[key]) for key in HODGE_KEYS)
    except (KeyError, TypeError, ValueError):
        return None


def factor_integer(value: int) -> dict[int, int]:
    """Factor a positive integer using trial division.

    The Smith invariants in this census are tiny, so a dependency-free factorer
    is preferable to pulling in a larger arithmetic path here.
    """

    remaining = abs(int(value))
    factors: dict[int, int] = {}
    divisor = 2
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            factors[divisor] = factors.get(divisor, 0) + 1
            remaining //= divisor
        divisor += 1 if divisor == 2 else 2
    if remaining > 1:
        factors[remaining] = factors.get(remaining, 0) + 1
    return factors


def torsion_profile(smith_normal_form: Iterable[Any]) -> dict[str, Any]:
    """Summarize torsion primes and p-primary exponents from Smith data."""

    invariant_factors = [int(value) for value in smith_normal_form if int(value) > 1]
    prime_exponents: dict[int, list[int]] = defaultdict(list)
    for invariant in invariant_factors:
        for prime, exponent in factor_integer(invariant).items():
            prime_exponents[prime].append(exponent)
    return {
        "torsion_invariant_factors": invariant_factors,
        "torsion_primes": sorted(prime_exponents),
        "p_primary_exponents": {str(prime): sorted(exponents) for prime, exponents in sorted(prime_exponents.items())},
    }


def _orbit_sizes(orbits: Iterable[Any]) -> tuple[int, ...]:
    return tuple(sorted(len(orbit) for orbit in orbits))


def _character_payload(character: Mapping[str, Any] | None) -> dict[str, Any]:
    if not character:
        return {"value_distribution": {}, "values": []}
    values = []
    for item in character.get("values", []):
        values.append(
            {
                "permutation": list(item.get("permutation", [])),
                "fixed_count": int(item.get("fixed_count", 0)),
            }
        )
    values.sort(key=lambda item: (item["permutation"], item["fixed_count"]))
    return {
        "value_distribution": {str(key): int(value) for key, value in sorted((character.get("value_distribution") or {}).items(), key=lambda kv: str(kv[0]))},
        "values": values,
    }


@dataclass(frozen=True, slots=True)
class SourceAssemblyRecord:
    """Normalized source-level assembly record for a validated spectrum."""

    arrangement_id: str
    validation_tier: str
    source_dataset: str
    source_reference: str
    inventory: tuple[int, ...]
    hodge: tuple[int, ...] | None
    hodge_source: str | None
    automorphism_group_order: int
    gluing_matrix_shape: tuple[int, int]
    rank_Q: int
    rank_F2: int
    kernel_dim_Q: int
    cokernel_dim_Q: int
    smith_normal_form: tuple[int, ...]
    plane_orbit_sizes: tuple[int, ...]
    double_line_orbit_sizes: tuple[int, ...]
    multiple_point_orbit_sizes: tuple[int, ...]
    character_C1: Mapping[str, Any]
    character_C0: Mapping[str, Any]

    @property
    def regime(self) -> str:
        return "CLEAN_TWO_STRATUM" if self.inventory[-1] == 0 else "TRUNCATED_TWO_STRATUM"

    @property
    def local_payload(self) -> dict[str, Any]:
        return {"inventory": dict(zip(INVENTORY_KEYS, self.inventory, strict=True)), "regime": self.regime}

    @property
    def rational_payload(self) -> dict[str, Any]:
        return {
            **self.local_payload,
            "gluing_matrix_shape": list(self.gluing_matrix_shape),
            "rank_Q": self.rank_Q,
            "kernel_dim_Q": self.kernel_dim_Q,
            "cokernel_dim_Q": self.cokernel_dim_Q,
        }

    @property
    def integral_payload(self) -> dict[str, Any]:
        return {**self.rational_payload, "smith_normal_form": list(self.smith_normal_form)}

    @property
    def equivariant_payload(self) -> dict[str, Any]:
        return {
            **self.integral_payload,
            "automorphism_group_order": self.automorphism_group_order,
            "plane_orbit_sizes": list(self.plane_orbit_sizes),
            "double_line_orbit_sizes": list(self.double_line_orbit_sizes),
            "multiple_point_orbit_sizes": list(self.multiple_point_orbit_sizes),
            "character_C1": _character_payload(self.character_C1),
            "character_C0": _character_payload(self.character_C0),
        }

    @property
    def hodge_refined_payload(self) -> dict[str, Any]:
        return {**self.local_payload, "hodge": None if self.hodge is None else dict(zip(HODGE_KEYS, self.hodge, strict=True))}

    @property
    def local_fingerprint(self) -> str:
        return stable_fingerprint("local", self.local_payload)

    @property
    def rational_fingerprint(self) -> str:
        return stable_fingerprint("rational", self.rational_payload)

    @property
    def integral_fingerprint(self) -> str:
        return stable_fingerprint("integral", self.integral_payload)

    @property
    def equivariant_fingerprint(self) -> str:
        return stable_fingerprint("equivariant", self.equivariant_payload)

    @property
    def hodge_refined_fingerprint(self) -> str:
        return stable_fingerprint("hodge_refined", self.hodge_refined_payload)

    @property
    def torsion(self) -> dict[str, Any]:
        return torsion_profile(self.smith_normal_form)

    def to_dict(self) -> dict[str, Any]:
        torsion = self.torsion
        return {
            "arrangement_id": self.arrangement_id,
            "validation_tier": self.validation_tier,
            "source_dataset": self.source_dataset,
            "source_reference": self.source_reference,
            "regime": self.regime,
            "inventory": dict(zip(INVENTORY_KEYS, self.inventory, strict=True)),
            "hodge": None if self.hodge is None else dict(zip(HODGE_KEYS, self.hodge, strict=True)),
            "hodge_source": self.hodge_source,
            "automorphism_group_order": self.automorphism_group_order,
            "gluing_matrix_shape": list(self.gluing_matrix_shape),
            "rank_Q": self.rank_Q,
            "rank_F2": self.rank_F2,
            "kernel_dim_Q": self.kernel_dim_Q,
            "cokernel_dim_Q": self.cokernel_dim_Q,
            "smith_normal_form": list(self.smith_normal_form),
            "plane_orbit_sizes": list(self.plane_orbit_sizes),
            "double_line_orbit_sizes": list(self.double_line_orbit_sizes),
            "multiple_point_orbit_sizes": list(self.multiple_point_orbit_sizes),
            "torsion_invariant_factors": torsion["torsion_invariant_factors"],
            "torsion_primes": torsion["torsion_primes"],
            "p_primary_exponents": torsion["p_primary_exponents"],
            "local_fingerprint": self.local_fingerprint,
            "rational_fingerprint": self.rational_fingerprint,
            "integral_fingerprint": self.integral_fingerprint,
            "equivariant_fingerprint": self.equivariant_fingerprint,
            "hodge_refined_fingerprint": self.hodge_refined_fingerprint,
            "realization_status": "SOURCE_ONLY",
        }


def normalize_spectrum(item: Mapping[str, Any], *, source_dataset: str) -> SourceAssemblyRecord:
    """Normalize one stored equivariant spectrum into a source assembly record."""

    arrangement_id = str(item["arrangement_id"])
    hodge_data = item.get("hodge_data_if_available") or item.get("hodge_data_if_known")
    hodge_value = hodge_tuple(hodge_data)
    validation_tier = "S2_HODGE_TABLE_LINKED" if hodge_value is not None else "S1_SOURCE_RECOMPUTED"
    if source_dataset == "fixed_equation_batch_001":
        validation_tier = "S2_HODGE_TABLE_LINKED"
    return SourceAssemblyRecord(
        arrangement_id=arrangement_id,
        validation_tier=validation_tier,
        source_dataset=source_dataset,
        source_reference=str(item.get("source_reference", "")),
        inventory=inventory_tuple(item.get("computed_inventory") or {}),
        hodge=hodge_value,
        hodge_source=(hodge_data or {}).get("source") if isinstance(hodge_data, Mapping) else None,
        automorphism_group_order=int(item["automorphism_group_order"]),
        gluing_matrix_shape=tuple(int(value) for value in item["gluing_matrix_shape"]),
        rank_Q=int(item["rank_Q"]),
        rank_F2=int(item["rank_F2"]),
        kernel_dim_Q=int(item["kernel_dim_Q"]),
        cokernel_dim_Q=int(item["cokernel_dim_Q"]),
        smith_normal_form=tuple(int(value) for value in (item.get("smith_normal_form") or [])),
        plane_orbit_sizes=_orbit_sizes(item.get("plane_orbits") or []),
        double_line_orbit_sizes=_orbit_sizes(item.get("double_line_orbits") or []),
        multiple_point_orbit_sizes=_orbit_sizes(item.get("multiple_point_orbits") or []),
        character_C1=item.get("character_C1") or {},
        character_C0=item.get("character_C0") or {},
    )


def group_records(records: Iterable[SourceAssemblyRecord], attr: str) -> dict[str, list[SourceAssemblyRecord]]:
    """Group records by a fingerprint attribute and keep members in natural order."""

    grouped: dict[str, list[SourceAssemblyRecord]] = defaultdict(list)
    for record in records:
        grouped[getattr(record, attr)].append(record)
    return {
        key: sorted(members, key=lambda record: natural_arrangement_key(record.arrangement_id))
        for key, members in sorted(grouped.items(), key=lambda item: natural_arrangement_key(item[1][0].arrangement_id))
    }
