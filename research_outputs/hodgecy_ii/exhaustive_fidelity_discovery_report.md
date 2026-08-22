# Exhaustive Fidelity Discovery Report

This report is exhaustive for the repo-local v1.0.0 evidence loaded by `scripts/hodgecy_ii_universe_deep_dive.py`. Production-root relationship tables were not available in this shell.

## 84/84a-Like Sets: Same Local Source Inventory And Same Ordinary Hodge Data

- `fixed_local_hodge_061`: 61, 451; local_inventory=p3=13;p4_0=6;p4_1=3;p5_0=0;p5_1=1;p5_2=0;l3=1; hodge=h12=0;h11=46;euler=92; member_count=2; source_level_result=same local source inventory and same ordinary Hodge data; node_level_result=unresolved
- `fixed_local_hodge_084`: 84, 84a; local_inventory=p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0; hodge=h12=0;h11=40;euler=80; member_count=2; source_level_result=same local source inventory and same ordinary Hodge data; node_level_result=unresolved
- `fixed_local_hodge_086`: 452, 453; local_inventory=p3=20;p4_0=9;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0; hodge=h12=0;h11=38;euler=76; member_count=2; source_level_result=same local source inventory and same ordinary Hodge data; node_level_result=unresolved

## 239/240/241-Like Sets: Repeated Local Inventory

- `local_signature_061`: 61, 451; member_count=2
- `local_signature_078`: 78, 79; member_count=2
- `local_signature_079`: 80, 455; member_count=2
- `local_signature_080`: 81, 454; member_count=2
- `local_signature_081`: 82, 245, 452, 453; member_count=4
- `local_signature_082`: 83, 84, 84a, 239, 240, 241; member_count=6
- `local_signature_083`: 85, 238; member_count=2

## Rational-Collapse / Integral-Separation Sets

- `rational_collapse_integral_006`: 84, 84a, 239, 240; integral_signature_count=2; source_level_result=same rational source assembly but different integral Smith data; node_level_result=unresolved

## Integral-Collapse / Equivariant-Separation Sets

- None found in the repo-local evidence for this run.

## Recurrent Rational Assembly Types

- `rational_signature_006`: 84, 84a, 239, 240; member_count=4

## Recurrent Integral Assembly Types

- `integral_signature_006`: 84, 240; member_count=2
- `integral_signature_007`: 84a, 239; member_count=2

## Recurrent Equivariant Source Types

- `equivariant_signature_006`: 84, 240; member_count=2
- `equivariant_signature_007`: 84a, 239; member_count=2

## Unusual Prime/Torsion Patterns

- `1`: 1; source_level_result=source assembly has nontrivial torsion profile
- `3`: 3; source_level_result=source assembly has nontrivial torsion profile
- `19`: 19; source_level_result=source assembly has nontrivial torsion profile
- `32`: 32; source_level_result=source assembly has nontrivial torsion profile
- `69`: 69; source_level_result=source assembly has nontrivial torsion profile
- `84`: 84; source_level_result=source assembly has nontrivial torsion profile
- `84a`: 84a; source_level_result=source assembly has nontrivial torsion profile
- `93`: 93; source_level_result=source assembly has nontrivial torsion profile
- `238`: 238; source_level_result=source assembly has nontrivial torsion profile
- `239`: 239; source_level_result=source assembly has nontrivial torsion profile
- `240`: 240; source_level_result=source assembly has nontrivial torsion profile
- `241`: 241; source_level_result=source assembly has nontrivial torsion profile
- `245`: 245; source_level_result=source assembly has nontrivial torsion profile

## Relevant Non-CKC Fidelity Examples

- Supplemental Cynk-Meyer `84a` is present outside the CKC numbering and participates in the strongest fixed-local/Hodge source-level split found here.

## Possible Future Problem-7.10 Targets

- `problem_7_10:84`: 84; 
- `problem_7_10:84a`: 84a; 

## Emerging Structure

The current repo-local evidence shows a hierarchy: local inventory can collapse multiple presentations, rational source assembly refines part of that collapse, integral Smith data refines more, and equivariant incidence data can still distinguish source presentations. The clearest source-level pattern remains the `84/84a/239/240/241` local fiber, with `84/84a` as the Hodge-refined source-level witness. This is not yet a node or LMHS statement.
