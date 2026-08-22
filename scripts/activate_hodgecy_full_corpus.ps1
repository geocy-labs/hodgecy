param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = [Environment]::GetEnvironmentVariable("HODGECY_DATA_ROOT", "User")
}

if ([string]::IsNullOrWhiteSpace($Root)) {
    throw "HODGECY_DATA_ROOT is not set at user scope. Set it to the production HodgeCY data root first."
}

if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "HODGECY_DATA_ROOT does not point to an existing directory."
}

$env:HODGECY_DATA_ROOT = (Resolve-Path -LiteralPath $Root).Path

python -c "import hodgecy, duckdb, pyarrow; from hodgecy import open_data_root; print(open_data_root(require_exists=True).root); print(hodgecy.__version__); print(duckdb.__version__); print(pyarrow.__version__)"
python scripts/hodgecy_full_corpus_doctor.py --root $env:HODGECY_DATA_ROOT
