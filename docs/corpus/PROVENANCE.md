# HodgeCY Provenance Model

HodgeCY keeps source records, presentations, abstract geometric claims, derived relationships, and theorem certificates separate. A row in a source table is not automatically a claim that two presentations define the same abstract Calabi--Yau object.

## Provenance Fields

The production catalog tracks:

- logical dataset identity and construction family;
- dataset/source instance and source revision;
- source format, locator, and source URL or DOI when available;
- checksum or integrity state for local source artifacts;
- adapter/schema and validation state;
- normalized table or native/lazy storage class;
- relationship evidence and claim status.

## Source Versus Derived Claims

Source-reported mathematical values remain source-reported unless HodgeCY has a separate validation or certificate. This is especially important for Hodge numbers, divisor topology, Chern/intersection data, cones, triangulations, group actions, and enumerative invariants.

## Large Data

Large sources use native/lazy or remote/native-lazy representations when full eager normalization would duplicate large external archives or erase source structure. Kreuzer--Skarke, CICY4 fibration archives, and ToricCY are handled with this boundary in mind.
