# Project record

Running log of the AlphaFold viral vs cellular accuracy study. Newest entries
go at the bottom.

Two kinds of entry: **[mentor]** for correspondence and meetings with
Dr. Blair G. Paul (Marine Biological Laboratory, Woods Hole), and **[code]**
for work landing in this repository. Code dates are commit dates, so they are
exact; mentor dates come from the email thread.

---

## May 2026

**May 22** [mentor] First contact from Blair, following the MBL visit to Millis
High School. Thread: "Following Up on AlphaFold Project".

**May 25 to May 27** [mentor] Exchange settling the research question: is
AlphaFold2 measurably less accurate on viral proteins than on human cellular
proteins, and does pLDDT track real error.

## June 2026

**Jun 2** [mentor] Three messages in one day working through scope and
approach.

**Jun 20** [code] First working pipeline. Downloads experimental structures
from RCSB and AlphaFold models by UniProt accession, superposes them with
TM-align, and writes per-protein metrics.

**Jun 23** [code] Added the sequence-coverage filter after noticing that some
viral proteins scored near zero for reasons unrelated to prediction quality.
This became the central methodological thread of the project.

**Jun 26 to Jun 29** [mentor] "Follow up meeting!" thread opened.

## July 2026

**Jul 1** [code] Added multiple regression, to ask whether viral origin
predicts accuracy once disorder and coverage are controlled for.

**Jul 2** [code] Added disorder-balanced protein selection and the per-residue
analysis layer, which measures local error per amino acid rather than per
protein.

**Jul 3 to Jul 8** [mentor] Four-message exchange.

**Jul 9** [code] Added figure captions generated from the real numbers, extra
robustness tests, and the cluster batch and merge tooling.

**Jul 20** [mentor] Sent "Alphafold progress" with four attachments: the first
substantive results report.

**Jul 20 to Jul 21** [code] Reorganised into `src/`, committed the protein
registry and generated cluster job files so the work was durable.

## August 2026

**Aug 2 to Aug 17** [mentor] Continued discussion on the progress thread.

**Aug 19** [mentor] Blair replied with an attachment.

**Aug 20** [mentor] Four messages in one afternoon.

**Aug 20** [code] Tidied the codebase and removed a duplicated disorder helper.

**Aug 25** [mentor] "Meeting again soon" thread opened; met and discussed
treating the raw viral/cellular gap with caution.

**Aug 25** [code] Moved fragment exclusion to selection time, so polyprotein
entries are kept out of the dataset rather than filtered from results. Added
one-command environment setup and the three-panel comparison figure.

**Aug 27** [code] Shipped ready-made 250 and 1000 protein registries so the
repository runs immediately after cloning.

**Aug 30** [mentor] Follow-up sent.

## September 2026

**Sep 1 to Sep 8** [mentor] Three exchanges.

**Sep 15** [mentor] Exchange with Blair; two attachments received.

**Sep 15** [code] Rewrote the README as plain-English setup instructions.

**Sep 16** [code] Fixed cluster batching, which had been splitting the registry
in file order and so handing whole batches a single group. Made the statistics
scripts able to read any metrics table, so merged cluster output can be
analysed.

**Sep 17** [code] Added NixOS support (conda cannot work there) and committed
the first full 250-protein run. Result at this point: 206 analysed, viral
median TM-score 0.912 against cellular 0.968.

**Sep 18** [code] **Found the largest defect in the project, in our own code.**
The downloader took the first model the AlphaFold API returned, which is
arbitrary when an accession is served as several. Poliovirus returns thirteen
models and the first is a 22-residue peptide, so a 283-residue capsid protein
was scored against it. Thirty-three proteins were affected, every one viral.
Fixed by selecting the model that actually contains the crystallised chain.

**Sep 19** [code] Re-ran the 250. Mismatches fell from 44 to 17, analysed rose
to 221, and 22 viral proteins recovered from TM-scores of roughly 0.03 to
roughly 0.97. **The viral effect survived**, which is the important part:
removing artifacts that penalised only the viral side did not remove the gap.

**Sep 22** [code] Changed selection to require that an AlphaFold model actually
covers the crystallised sequence, rather than merely exist. Rebuilt both
registries. Also fixed a defect of our own making, where a cache marker keyed
on accession alone let a model chosen for one mature chain be reused against a
different one.

**Sep 22** [code] Final run: **4 mismatches of 250**, down from 44. 233
proteins analysed, 114 viral and 119 cellular.

**Sep 23** [code] Corrected stale documentation and made the default registry
refresh automatically, after finding it had drifted 49 proteins out of date.
Verified the whole thing from a clean clone with no cache.

---

## Where the result stands

| dataset version | mismatches | analysed | is_viral p |
|---|---|---|---|
| original | 44 (39 viral) | 206 | 2.8e-07 |
| after model-selection fix | 17 (12 viral) | 221 | 5.2e-07 |
| after coverage-validated selection | **4** | **233** | **2.6e-06** |

Viral proteins are predicted less accurately: median TM-score 0.927 against
0.970, p = 1.3e-08. Both viral origin (p = 2.6e-06) and disorder (p = 1.8e-06)
predict accuracy independently, and they are not confounded.

The finding held across three rebuilds of the dataset, each after fixing a
defect that penalised the viral side almost exclusively. Each fix should have
shrunk the gap if the gap were an artifact. It did not move.

## Open items

- Selection takes the first N proteins in database return order. Deterministic
  and reproducible, but not a random sample.
- The viral pool is capped at 375, so a balanced set cannot exceed 750.
- The top disorder bin holds too few proteins to test, because disorder impedes
  crystallisation.
- `nix/fhs.nix` has not been evaluated by Nix itself; everything downstream of
  it has been tested.
- Cluster jobs are generated but not submitted; they need an account and a
  partition.
