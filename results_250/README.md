# Results: 250-protein run

Output of `src/af_study.py` on `proteins_250.csv` (125 viral, 125 cellular),
plus `compare_metrics.py` and `extra_stats.py`. Committed because the run takes
time and the figures are needed for presentations.

Regenerate with:

    python src/af_study.py --registry proteins_250.csv
    python src/compare_metrics.py
    python src/extra_stats.py

## What is in the analysed set

Of the 250: 4 excluded outright (experimental chain outside the 50 to 600
resolved-residue window), 4 flagged as sequence mismatches, 11 flagged as too
poorly resolved, leaving **233 analysed (114 viral, 119 cellular)**.

| | viral | cellular |
|---|---|---|
| median TM-score | 0.927 | 0.970 |
| median RMSD | 1.53 A | 0.99 A |
| median pLDDT | 78.9 | 87.9 |
| median disorder | 10.7% | 12.4% |

## Headline results

Viral proteins are predicted less accurately. Mann-Whitney on TM-score gives
p = 1.3e-08, rank-biserial r = -0.431, and Welch's t-test agrees. RMSD agrees
under both tests too.

Regression `tm_score ~ disorder + coverage + is_viral`, n = 233:

- `is_viral`  coef -0.094, **p = 2.6e-06**
- `disorder`  coef -0.242, **p = 1.8e-06**
- `coverage`  coef +0.065, p = 0.87

Viral origin and disorder each predict accuracy independently. Viral proteins
are not the more disordered group here (10.7% against 12.4%, p = 0.14), and all
VIFs are near 1.0, so the two effects are not confounded.

## Why this result is trustworthy

The same finding survived three versions of the dataset, each built after
fixing a defect that had been inflating the viral deficit:

| dataset | mismatches | analysed | is_viral p |
|---|---|---|---|
| original | 44 (39 viral) | 206 | 2.8e-07 |
| after AlphaFold model-selection fix | 17 (12 viral) | 221 | 5.2e-07 |
| after coverage-validated selection | **4** | **233** | **2.6e-06** |

Each fix removed artifacts that fell almost entirely on the viral side, so each
should have shrunk or erased the gap if the gap were an artifact. It did not
move. That is the strongest argument available that the effect is real.

Disorder became significant only after the first fix. In the original dataset
its effect was masked by 33 viral proteins carrying near-zero scores for
reasons unrelated to disorder.

## The 4 remaining flagged proteins

| protein | coverage | TM | pLDDT |
|---|---|---|---|
| P1/Mahoney poliovirus (VP4) | 0.783 | 0.236 | 58 |
| Coxsackievirus A9 (VP4) | 0.787 | 0.230 | 60 |
| Ewing's tumor-associated antigen 1 | 0.409 | 0.388 | 49 |
| G(i) subunit alpha-1 | 0.764 | 0.835 | 94 |

The two VP4 capsid subunits sit just under the 0.80 cutoff. The threshold was
deliberately not lowered to admit them: tuning a cutoff until awkward cases
pass is the criticism this filter exists to withstand. Both are predicted at
100 percent disorder with pLDDT near 58, which is the signature of a genuine
prediction failure rather than an indexing artifact, VP4 having little
independent structure outside the assembled virion.

## The mechanism test: ESMFold

`src/esmfold_compare.py` runs the same proteins through ESMFold, which predicts
structure from a protein language model and uses no sequence alignment. The
question is whether AlphaFold2's viral deficit comes from its alignment step.
211 proteins were scored by both programs (106 viral, 105 cellular); 22 were
excluded because the ESMFold API accepts at most 400 residues.

| | AlphaFold2 | ESMFold |
|---|---|---|
| viral median TM-score | 0.917 | 0.824 |
| cellular median TM-score | 0.968 | 0.954 |
| **viral gap** | **0.051** | **0.130** |
| regression, is_viral coef | -0.098 | -0.226 |
| regression, disorder coef | -0.232 | -0.238 |

**The viral gap more than doubles when the alignment is taken away.**
AlphaFold2's per-protein advantage over ESMFold is about five times larger on
viral proteins (median +0.033) than on cellular ones (+0.006), Mann-Whitney
p = 0.0014. So the alignment step is not the cause of AlphaFold2's viral
deficit. If anything it partly rescues viral proteins, and without it they fall
further behind.

**Disorder and viral origin behave differently.** The disorder penalty is the
same under both programs (-0.232 against -0.238), so it behaves like a property
of the protein: hard regardless of method. The viral penalty more than doubles
between programs, so it behaves like a limitation of the methods, tied to how
well viral proteins are represented in the sequence data both programs learned
from. That maps directly onto the project's question, though as a pattern, not
a proof of mechanism.

ESMFold's confidence tracks its own error closely (pLDDT against TM-score,
rho = +0.81), more tightly than AlphaFold2's.

Caveat: ESMFold's language model was itself trained on sequence databases in
which viral proteins are under-represented, so this rules out alignments
specifically as the cause, not data scarcity in general.

## Known limitations

- **Sampling is not random.** The list takes the first N of each pool in
  database return order. Deterministic and reproducible, but not a random
  sample, and no amount of mismatch filtering changes that.
- **The viral pool is capped at 375.** That is every viral protein in the PDB
  meeting all criteria with an AlphaFold model that covers it, so a balanced
  set cannot exceed 750.
- **The top disorder bin is nearly empty**, because disorder impedes
  crystallisation. Any disorder effect measured against crystal structures is
  more likely understated than overstated.
- **Coverage is no longer cleanly bimodal** as it was in the 79-protein pilot,
  so the 0.80 threshold does affect membership and should not be described as
  arbitrary. With only 4 proteins now flagged, little rests on it.
