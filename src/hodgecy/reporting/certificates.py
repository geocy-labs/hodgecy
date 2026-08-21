from __future__ import annotations

from typing import Any, Iterable

from hodgecy.certificates import CertificateRegistryRecord, LegacyReleaseCertificateSummary, certificate_summary_rows


def certificate_status_rows(records: Iterable[CertificateRegistryRecord]) -> list[dict[str, Any]]:
    return certificate_summary_rows(records)


def legacy_release_status_row(summary: LegacyReleaseCertificateSummary) -> dict[str, Any]:
    row = summary.to_dict()
    row["status"] = "legacy_verified_by_checksum_manifest"
    row["artifact_class"] = "certified"
    row["schema_version"] = "legacy_v0.2.0_release_manifest"
    return row


def certificate_status_report(records: Iterable[CertificateRegistryRecord]) -> dict[str, Any]:
    rows = certificate_status_rows(records)
    by_purpose: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        by_purpose[str(row["purpose"])] = by_purpose.get(str(row["purpose"]), 0) + 1
        by_status[str(row["status"])] = by_status.get(str(row["status"]), 0) + 1
    return {"certificate_count": len(rows), "by_purpose": dict(sorted(by_purpose.items())), "by_status": dict(sorted(by_status.items())), "rows": rows}
