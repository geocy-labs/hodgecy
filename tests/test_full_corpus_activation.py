from __future__ import annotations

import os
from pathlib import Path

import pytest

from hodgecy.core.errors import ConfigurationError
from hodgecy.research.full_corpus_context import FullCorpusContext

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_full_corpus_mode_refuses_missing_data_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HODGECY_DATA_ROOT", raising=False)
    with pytest.raises(ConfigurationError):
        FullCorpusContext.open()


@pytest.mark.skipif(not os.environ.get("HODGECY_DATA_ROOT"), reason="production HODGECY_DATA_ROOT is not configured")
def test_full_corpus_context_opens_production_catalog() -> None:
    context = FullCorpusContext.open()
    counts = context.summary_counts()

    assert counts["logical_dataset_count"] == 53
    assert counts["instance_count"] == 80
    assert counts["physical_source_count"] == 187
    assert counts["query_table_count"] == 32
    assert counts["source_data_record_count"] == 574_616_978
    assert len(context.relationship_tables) == 4


@pytest.mark.skipif(not os.environ.get("HODGECY_DATA_ROOT"), reason="production HODGECY_DATA_ROOT is not configured")
def test_doctor_readiness_artifact_is_path_redacted() -> None:
    import importlib.util

    def load_script(name: str):
        path = REPO_ROOT / "scripts" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    hodgecy_full_corpus_doctor = load_script("hodgecy_full_corpus_doctor")

    assert hodgecy_full_corpus_doctor.main([]) == 0

    output = Path("research_outputs/hodgecy_ii/final/reproduction/full_corpus_doctor/full_corpus_readiness.json").read_text(encoding="utf-8")
    assert "FULL_HODGECY_V1_CORPUS_READY" in output
    assert os.environ["HODGECY_DATA_ROOT"] not in output
