# Known Limitations And Future Dataset Updates

The initial HodgeCY acquisition program is complete. Future discoveries should be treated as versioned corpus updates, not as Wave 5.

## Final Known Exceptions

- **DESY CICY GV h11=9:** represented as `SOURCE_CORRUPT`; the archive is ZIP-shaped but reproducibly fails decompression, and no repaired authoritative public copy was found.
- **Genuine gCICY APS supplements:** `g21N5.mx` and `g21N6.mx` are verified native Wolfram sources. HodgeCY does not claim a normalized row count until a Wolfram-compatible export is run.
- **ToricCY:** represented as remote/native-lazy with 4,434,624,498 advertised bytes and 7 top-level assets, not as a fully normalized local mirror.
- **Pfaffian/determinantal Calabi--Yau sources:** source-registry-only because no broad public machine-readable corpus was found.
- **Integral topology/torsion:** source-registry-only because no broad canonical machine-readable table was found.

## Future Update Registry

| Category | Known source | Current state | Update trigger | Priority |
| --- | --- | --- | --- | --- |
| SOURCE_CORRUPT | DESY CICY GV h11=9 | SOURCE_CORRUPT | authoritative repaired archive appears | P0_future_update |
| SOURCE_REGISTRY_ONLY | Pfaffian/determinantal CY literature/code | SOURCE_REGISTRY_ONLY | public corpus/table released | P2_future_update |
| SOURCE_REGISTRY_ONLY | integral topology/torsion literature | SOURCE_REGISTRY_ONLY | systematic table/database released | P2_future_update |
| FUTURE_DATASET_UPDATE | ToricCY | REMOTE_NATIVE_LAZY | new release or terms-cleared local mirroring need | P1_future_update |
| FUTURE_DATASET_UPDATE | APS gCICY supplements | COMPLETE_NATIVE_SOURCE | Wolfram-compatible exporter available | P1_future_update |
