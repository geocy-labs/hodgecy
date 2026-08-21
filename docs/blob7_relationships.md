# Blob 7 Relationship And Enrichment Infrastructure

Blob 7 introduces a typed relationship layer for joins, fibrations, group actions, and quotient enrichments. The layer records what a source or computation supports without promoting weak evidence into geometric identity.

## Relationship Assertions

`hodgecy.core.relationships.RelationshipAssertion` now carries:

- typed `RelationshipType` values such as `source_crosswalk`, `fibration_of`, `free_action_on`, and `quotient_of`
- typed `EvidenceType` values such as `SOURCE_EXPLICIT`, `EXACT_SOURCE_ID`, and `COMPUTATION_CERTIFIED`
- `JoinState` for exact, unmatched, ambiguous, dangling, and unresolved joins
- endpoint-level dataset and native identifiers
- source dataset, source record, locator, provenance, validation events, and payload metadata
- schema marker `hodgecy.relationship` / `relationship.v1`

Legacy construction remains available: `RelationshipEndpoint(object_id, role)` and direct `RelationshipAssertion(...)` construction still work.

## Join Policy

The public join builders live in `hodgecy.relationships`:

- `exact_source_crosswalk` materializes only unambiguous exact source-key relationships.
- `one_to_many_relationships` materializes parent-to-child relationships only when the parent endpoint exists.
- unmatched, ambiguous, and dangling rows become rejection records rather than invented geometry IDs.

The guard functions in `hodgecy.relationships.policies` intentionally reject common invalid promotions:

- matching Hodge numbers are not geometry identity
- swapped Hodge numbers are not mirror certification
- exact weight-vector crosswalks are source or presentation relationships
- source-reported free actions are not computational freeness certificates

## Geometry Enrichment Payloads

`hodgecy.geometry.fibrations.FibrationPayload` lowers source fibration records into `fibration_of` or `nested_fibration_of` relationships.

`hodgecy.geometry.symmetry` provides:

- `GroupPayload`
- `GroupActionPayload`, lowering to `free_action_on` or `involution_on`
- `QuotientPayload`, lowering to `quotient_of`

These payloads preserve source claims and only use computational certification when explicitly marked as certified.

## Storage And Query

`HodgeCYCatalog.register_parquet_source` accepts `table_kind`, `metadata`, `parent_key`, and `child_key`. Relationship and fibration tables therefore remain discoverable through `list_tables(TableKind.RELATIONSHIP)` and `list_tables(TableKind.FIBRATION)` while still using the existing columnar query engine.

`RelationshipQueryService` is a small query wrapper for relationship tables. It supports outgoing, incoming, count, existence, and projected related-record queries.