# Results: 250-protein run

Output of `python src/af_study.py` on `proteins_250.csv` (125 viral, 125
cellular), plus `compare_metrics.py` and `extra_stats.py`. Committed because
these took an hour to produce and the figures are needed for presentations.

Regenerate with:

    python src/af_study.py --registry proteins_250.csv
    python src/compare_metrics.py
    python src/extra_stats.py

## Headline numbers

All 250 proteins processed without error. 44 were flagged as sequence
mismatches and excluded, leaving 206 (86 viral, 120 cellular).

| | viral | cellular |
|---|---|---|
| median TM-score | 0.912 | 0.968 |
| median RMSD | 1.49 A | 0.96 A |
| median pLDDT | 79.1 | 86.8 |
| flagged as mismatches | 39 of 125 | 5 of 125 |

Mann-Whitney on TM-score: p = 7.6e-10, rank-biserial r = -0.503.

Regression `tm_score ~ disorder + coverage + is_viral` on the 206:
is_viral is significant (p = 2.8e-07), disorder is not (p = 0.073).
All VIFs are near 1.0, so the predictors are not collinear. Full model
R-squared is 0.143.

Note that this reverses the direction of the earlier 79-protein pilot, in
which disorder was significant and viral origin was not. See the top-level
README and the project brief for discussion.
