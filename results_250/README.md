# Results: 250-protein run

Output of `src/af_study.py` on `proteins_250.csv` (125 viral, 125 cellular),
plus `compare_metrics.py` and `extra_stats.py`. Committed because the run takes
about an hour and the figures are needed for presentations.

Regenerate with:

    python src/af_study.py --registry proteins_250.csv
    python src/compare_metrics.py
    python src/extra_stats.py

## What is in the analysed set

Of the 250 proteins: 6 excluded outright (experimental chain outside the 50 to
600 resolved-residue window), 17 flagged as sequence mismatches, 12 flagged as
too poorly resolved, leaving **221 analysed (105 viral, 116 cellular)**.

| | viral | cellular |
|---|---|---|
| median TM-score | 0.920 | 0.970 |
| median RMSD | 1.48 A | 0.96 A |
| median pLDDT | 79.0 | 86.8 |
| median disorder | 10.9% | 14.6% |

## Headline results

Viral proteins are predicted less accurately. Mann-Whitney on TM-score gives
p = 3.5e-09 with rank-biserial r = -0.460, and Welch's t-test agrees
(p = 1.8e-06). The RMSD comparison now also agrees under both tests, which it
did not in earlier runs.

Regression `tm_score ~ disorder + coverage + is_viral` on the 221:

- `is_viral`  coef -0.102, **p = 5.2e-07**
- `disorder`  coef -0.174, **p = 0.00067**
- `coverage`  coef +0.050, p = 0.89

Both viral origin and disorder independently predict accuracy. All VIFs are
near 1.0, and viral proteins are not more disordered than cellular ones here
(10.9% against 14.6%, p = 0.20), so the two effects are not confounded. Full
model R-squared is 0.155 against 0.047 for disorder alone.

## How this supersedes the earlier run

An earlier version of this run reported 206 analysed proteins and a viral
median TM-score of 0.912, with disorder not significant (p = 0.073). That run
was affected by a defect in `download_alphafold`, which took the first model
the AlphaFold API returned. For an accession served as several per-chain models
that choice is arbitrary: poliovirus returned thirteen and the first was a
22-residue peptide.

Thirty-three proteins got a partial model that way, every one of them viral.
Fixing the selection recovered 22 of them into the analysed set, with TM-scores
rising from 0.03 to 0.34 up to 0.94 to 0.99.

**The viral effect survived the correction.** That matters more than the
correction itself: removing 22 artifact-driven viral failures did not remove
the gap, which is what would have happened had the gap been an artifact.

## Known limitations

- **Coverage is no longer cleanly bimodal.** In the 79-protein pilot, flagged
  proteins sat at or below 0.23 and kept ones at or above 0.90, so the
  threshold could be called arbitrary without consequence. Here the flagged
  values run from 0.08 to 0.80 more or less continuously, with only a 0.035 gap
  below the 0.80 cutoff. The choice of threshold now affects which proteins are
  included, and that should be stated rather than defended.
- **`proteins_250.csv` predates two selection fixes.** Entities mapping to more
  than one UniProt accession are now dropped at selection, but this list was
  built before that, so engineered fusions are still present and account for
  several of the 17 flagged proteins. Rebuilding the lists would remove them.
- **Sampling is not random.** The list takes the first 125 of each pool in
  database return order. Deterministic and reproducible, but not a random
  sample.
- **The top disorder bin is nearly empty** (n = 2 of 221), because disorder
  impedes crystallisation. Any disorder effect measured this way is more likely
  understated than overstated.
