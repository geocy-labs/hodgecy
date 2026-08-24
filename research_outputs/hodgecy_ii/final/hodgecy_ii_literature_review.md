# HodgeCY II Literature Review

Status: `SOURCE_CHECKED`  
Review date: `2026-08-24`

## Literature Map

Kreuzer and Skarke's classification of four-dimensional reflexive polytopes is the classical large-scale toric-hypersurface context: 473,800,776 polytopes collapse to 30,108 distinct Hodge-number pairs. HodgeCY II therefore does not claim to discover Hodge-number degeneracy; it treats that known many-to-one collapse as motivation for finer source-aware fidelity layers.

Ashmore and He study statistical and fractal structure in Calabi-Yau threefold data. The source-checked multiplicities include 15,067,026 self-mirror entries and large same-Hodge fibers such as 910,113 for `(27,27)`, 877,191 for `(25,25)`, and 875,275 for `(26,26)`. This directly rejects any novelty claim of the form "no previous work has found >10,000 Calabi-Yau collisions" when collision means repeated Hodge data or similarly coarse numerical data.

Cynk and van Straten provide the most directly adjacent double-octic precedent. Their Picard-Fuchs work shows that coarse Hodge information for octic arrangements can be refined by birational/period data; HodgeCY II is likewise a double-octic refinement problem, but it uses source assembly, rational/integral lattice data, equivariance, and verified block-evaluation layers rather than Picard-Fuchs operators.

Grimm, Ruehle, and van de Heisteeg use limiting mixed Hodge structures and infinite-distance limits to refine Calabi-Yau classification data. Their invariant is not identified with HodgeCY source assembly or Hodge atoms here; the relation is conceptual adjacency: degeneration-sensitive Hodge-theoretic information can refine ordinary topological/Hodge information.

Brodie, Constantin, Lukas, and Ruehle study extended Kahler/effective cones for h11=2 Calabi-Yau threefolds drawn from CICY and Kreuzer-Skarke constructions. This is useful adjacent precedent for systematic cross-construction comparison, but it is not equivalent to HodgeCY's source-fidelity hierarchy.

Chandra, Constantin, Fraser-Taliente, Harvey, and Lukas are especially important adjacent prior art. Their work bounds diffeomorphism classes in the Kreuzer-Skarke list using Hodge numbers, triple-intersection data, second Chern class data, and integral basis-change/equivalence checks. HodgeCY II should be framed as a different refinement ladder: local and Hodge data, rational source assembly, integral source lattice, equivariant structure, and later geometric relation/evaluation layers.

Geramita, Harbourne, and Migliore give standard star-configuration context. Definition 2.1 imposes a proper-meeting hypothesis; Proposition 2.9 gives ACM/Hilbert data under that hypothesis, while Proposition 2.6 gives the basic-double-link construction. The full proper-meeting theorem is stronger than the verified 84/84a hypotheses because higher-order point concurrences are allowed, so HodgeCY II cites it as context and uses the basic-double-link framework plus an explicit Hilbert-Burch matrix.

Burch, Bruns-Herzog, and Eisenbud supply the Hilbert-Burch theorem references used for the rank-seven syzygy package attached to the eight sevenfold-product generators.

## Conservative Novelty Statement

Rejected claim: **No previous work has found >10,000 Calabi-Yau collisions.**

Reason: large degeneracies under Hodge numbers and other coarse invariants are already documented in the Kreuzer-Skarke distribution and later statistical studies.

Conservative HodgeCY II claim:

> Large degeneracies of Calabi-Yau data under Hodge numbers and other coarse invariants are well known, and previous work has refined them using intersection data, Chern classes, Picard-Fuchs operators, degeneration data, and integral topological invariants. What appears absent in the literature reviewed here is a source-aware computational fidelity census that records where presentations first separate along a hierarchy of local, Hodge, rational source-assembly, integral source-lattice, equivariant, and later geometric relation/evaluation invariants.

## Source-Checked References

| key | reference | checked metadata |
| --- | --- | --- |
| KreuzerSkarke2000 | Maximilian Kreuzer and Harald Skarke, *Complete classification of reflexive polyhedra in four dimensions* | arXiv `hep-th/0002240`; DOI `10.4310/ATMP.2000.v4.n6.a2`; `https://arxiv.org/abs/hep-th/0002240` |
| AshmoreHe2011 | Anthony Ashmore and Yang-Hui He, *Calabi-Yau Three-folds: Poincare Polynomials and Fractals* | arXiv `1110.1612`; DOI `10.1142/9789814412551_0007`; `https://arxiv.org/abs/1110.1612` |
| CynkVanStraten2019 | Slawomir Cynk and Duco van Straten, *Picard-Fuchs operators for octic arrangements I. The case of orphans* | arXiv `1709.09752`; DOI `10.4310/CNTP.2019.v13.n1.a1`; `https://arxiv.org/abs/1709.09752` |
| GrimmRuehleVanDeHeisteeg2021 | Thomas W. Grimm, Fabian Ruehle, and Damian van de Heisteeg, *Classifying Calabi-Yau Threefolds Using Infinite Distance Limits* | arXiv `1910.02963`; DOI `10.1007/s00220-021-03972-9`; `https://arxiv.org/abs/1910.02963` |
| BrodieConstantinLukasRuehle2022 | Callum R. Brodie, Andrei Constantin, Andre Lukas, and Fabian Ruehle, *Geodesics in the extended Kahler cone of Calabi-Yau threefolds* | arXiv `2108.10323`; DOI `10.1007/JHEP03(2022)024`; `https://arxiv.org/abs/2108.10323` |
| ChandraConstantinFraserTalienteHarveyLukas2024 | Aditi Chandra, Andrei Constantin, Cristofero S. Fraser-Taliente, Thomas R. Harvey, and Andre Lukas, *Enumerating Calabi-Yau Manifolds: Placing Bounds on the Number of Diffeomorphism Classes in the Kreuzer-Skarke List* | arXiv `2310.05909`; DOI `10.1002/prop.202300264`; `https://arxiv.org/abs/2310.05909` |
| GeramitaHarbourneMigliore2013 | Anthony V. Geramita, Brian Harbourne, and Juan Migliore, *Star configurations in P^n* | arXiv `1203.5685`; DOI `10.1016/j.jalgebra.2012.11.034`; `https://arxiv.org/abs/1203.5685` |
| Burch1968 | Lindsay Burch, *On ideals of finite homological dimension in local rings* | DOI `10.1017/S0305004100043620`; `https://doi.org/10.1017/S0305004100043620` |
| BrunsHerzog1998 | Winfried Bruns and Jurgen Herzog, *Cohen-Macaulay Rings* | Cambridge University Press; Theorem 1.4.17 used as standard Hilbert-Burch reference |
| Eisenbud1995 | David Eisenbud, *Commutative Algebra with a View Toward Algebraic Geometry* | Springer; DOI `10.1007/978-1-4612-5350-1`; Theorem 20.15 used as standard Hilbert-Burch reference |

