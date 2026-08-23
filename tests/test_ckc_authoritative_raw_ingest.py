from __future__ import annotations

from hodgecy.research.ckc_authoritative_raw_ingest import (
    build_ingest_manifest,
    parse_arrangement_equations,
    parse_parameter_conditions,
    parse_tex_blocks,
)


def test_parse_authoritative_tex_arrangement_equations() -> None:
    source_files = [
        {
            "path": "sample.tex",
            "file_type": "tex",
            "raw_text": r"""
\section{Equations and Data}\label{sec:EqsData}
\subsection{Equations}
\noindent\parbox[right]{9mm}{\textbf{451:}}\parbox{3mm}{\hfill}%
\parbox[t]{15cm}{\((x + \frac{\sqrt{-3} - 1}2y)xy(y + t)(x + t)z(z + t)(x+y+z+t)\)}

\noindent\parbox[right]{9mm}{\textbf{452:}}\parbox{3mm}{\hfill}%
\parbox[t]{15cm}{\(xy(\frac{\sqrt{-3} + 3}2x + y + \frac{\sqrt{-3} + 3}2z)zt(y+z)(x+y+z+t)\)}
""",
        }
    ]
    pages = [
        {
            "page_number": 1,
            "detected_equation_table_figure_identifiers": {"arrangement_ids": ["451", "452"]},
        }
    ]

    equations = parse_arrangement_equations(source_files, pages)

    assert [row["arrangement_id"] for row in equations] == ["451", "452"]
    assert equations[0]["page_number"] == 1
    assert equations[0]["algebraic_constants"] == [r"\sqrt{-3}"]
    assert equations[1]["raw_equation_block_id"] == "ckc_equation_452"


def test_parse_tex_blocks_and_parameter_conditions() -> None:
    source_files = [
        {
            "path": "sample.tex",
            "file_type": "tex",
            "raw_text": r"""
\section{Classification}
The ideal $I$ is saturated by $J$ and Arrangement No. 451 has a Galois remark.
\begin{lstlisting}
function IncidenceTable(OcticArr);
end function;
\end{lstlisting}
\begin{tabular}{|r|r|}
1 & 2\\
\end{tabular}
""",
        }
    ]

    blocks = parse_tex_blocks(source_files)
    conditions = parse_parameter_conditions(blocks, [{"arrangement_id": "451"}])

    assert any(block["block_kind"] == "code" for block in blocks)
    assert any(block["block_kind"] == "table" for block in blocks)
    assert conditions[0]["linked_arrangements"] == ["451"]


def test_ingest_manifest_flags_complete_raw_layer() -> None:
    manifest = build_ingest_manifest(
        {
            "arxiv_id": "2602.19413",
            "arxiv_version": "v1",
            "pdf_acquired": True,
            "source_files_ingested": 3,
            "pdf_page_count": 50,
            "pdf_pages_ingested": 50,
            "tables_ingested": 1,
            "arrangement_equations_found": 455,
            "missing_ckc_ids": [],
            "code_blocks_found": 1,
            "ckc_dossiers_built": 455,
        }
    )

    assert all(manifest["completeness_flags"].values())
