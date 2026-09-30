# Project record

Running log of the AlphaFold viral vs cellular accuracy study. Newest entries
go at the bottom.

Entries are tagged **[mentor]** for work with Dr. Blair Paul, **[school]** for
the STEAM senior project track, and **[code]** for work landing in this
repository. Code dates are commit dates and so are exact to the day.

---

## Mentor

**Dr. Blair G. Paul**, Assistant Scientist, Marine Biological Laboratory,
7 MBL Street, Woods Hole, MA 02543.

Dr. Paul is a research scientist at the MBL, an independent research institution
affiliated with the University of Chicago and one of the oldest marine
biological laboratories in the United States. His work centres on microbial
genomics and the evolution of genetic elements in marine microorganisms.

The mentorship began after his visit to Millis High School. His role is
scientific supervision rather than day-to-day direction: he advises on
experimental design, reviews results and their interpretation, checks the
statistical reasoning, and guides the shape of the eventual write-up. The
implementation, analysis and code are mine.

## Research question and hypothesis

**Question.** Is AlphaFold2 measurably less accurate on viral proteins than on
human cellular proteins, and does its own confidence score, pLDDT, track real
prediction error?

**Hypothesis.** Viral proteins would be predicted less accurately, because
AlphaFold2 relies on multiple sequence alignments and viral proteins have fewer
detectable homologues to align against. Intrinsic disorder was expected to act
as a confounding variable, being associated both with prediction difficulty and
with viral proteomes.

---

## May 2026

**May 22, 8:00 AM** [mentor] Initial outreach to Dr. Paul, following the MBL
visit to Millis High School. Thread: "Following Up on AlphaFold Project".

**May 22, 4:10 PM** [mentor] Dr. Paul replied the same day.

**May 25 to May 27** [mentor] Exchange settling the research question and
scope.

## June 2026

**Jun 2** [mentor] **Meeting with Dr. Blair Paul.** Agreed action items:

- build a summer timeline with timestamps
- write a blurb on Dr. Paul's credentials and his role as mentor
- link any draft paper sections
- state the research question and hypothesis
- plan a timeline running into the school year
- prepare a presentation for the start of the school year: present where the
  project is and where it is going, via good slides. Ms. Cheney and Dr. Paul
  would then draft the STEAM senior contract on the spot, to be agreed then,
  with any later changes agreed by all parties.

Three messages followed the same day.

**Jun 20** [code] First working pipeline. Downloads experimental structures
from RCSB and AlphaFold models by UniProt accession, superposes them with
TM-align, writes per-protein metrics.

**Jun 23** [code] Added the sequence-coverage filter, after noticing that some
viral proteins scored near zero for reasons unrelated to prediction quality.
This became the central methodological thread of the project.

**Jun 26, 10:04 AM** [mentor] Progress sent to Dr. Paul. Set expanded to **56
proteins**, pulled systematically from RCSB rather than hand-picked. Early
result: AlphaFold2 significantly more accurate on cellular than viral proteins,
**median TM 0.96 against 0.88, p = 0.0007**, with disorder also tracking
accuracy. Flagged a scope change in the same message: some viral outliers
looked like fragment mismatches rather than real prediction errors, where the
AlphaFold fragment does not contain the crystallised domain, so a coverage
filter was being added and the framing might lean more on disorder and
coverage than on viral against cellular alone.

**Jun 29, 10:22 PM** [mentor] Follow-up nudge.

## July 2026

**Jul 1** [code] Added multiple regression, to ask whether viral origin
predicts accuracy once disorder and coverage are controlled for.

**Jul 2** [code] Added disorder-balanced selection and the per-residue analysis
layer, measuring local error per amino acid rather than per protein.

**Jul 3, 2:33 PM** [mentor] Dr. Paul proposed a Zoom for the 8th or 9th, asked
how the proteins were chosen systematically and whether a shareable table of
accessions and annotated functions existed, and shared a then-new Nucleic Acids
Research paper on using fold prediction (Foldseek, with protein fold class
databases) to annotate phage genomes more accurately than sequence-homology
tools such as HMMER.

**Jul 5, 6:12 PM** [mentor] Reply describing the selection procedure in full:
pull viral and human structures from RCSB, filter by resolution, deduplicate by
UniProt accession, confirm an AlphaFold model exists, then balance across four
disorder levels, giving **79 proteins**. Noted working 9 to 5 at BWSI through
this period, so meetings had to be evenings.

**Jul 8, 9:19 AM** [mentor] Asked to move 15 minutes earlier because of train
delays.

**Jul 8, 5:15 PM** [mentor] **Zoom meeting held with Dr. Paul.**

**Jul 9** [code] Added figure captions generated from the real numbers, extra
robustness tests, and the cluster batch and merge tooling.

**Jul 20, 8:41 AM** [mentor] Results report sent with four figures. On the
coverage-filtered set, Mann-Whitney gave viral against cellular medians of
**0.95 and 0.965, p = 0.052**, so the narrowed gap was not statistically
significant, and in the follow-up regression the small remainder was carried by
intrinsic disorder rather than by the proteins being viral. Figures sent: the
TM boxplot, pLDDT against TM with fragment artifacts marked, disorder against
TM, and the per-residue hexbin. Also noted reading the Phold paper, whose
confidence metric correlates with structure quality much as pLDDT does.

**Jul 20 to Jul 21** [code] Reorganised into `src/`, committed the protein
registry and generated cluster job files so the work was durable.

## August 2026

**Aug 2, 10:04 PM** [mentor] Cluster job files expected by Wednesday.

**Aug 4, 5:00 PM** [school] **Meeting with Ms. Copice.** Status reported:

- met with Dr. Paul roughly three weeks earlier
- started drafting the methods section; the methods approach looks sound
- Dr. Paul out of contact at present; will review results once back in touch
- hoping to begin drafting the paper
- may post a preprint
- possibly run a literature review, then follow up with the introduction

**Aug 12, 3:02 PM** [mentor] Dr. Paul checked in, having been occupied with a
grant proposal, and proposed a Zoom the following week.

**Aug 17, 10:49 PM** [mentor] Proposed the 20th at 3 PM.

**Aug 19, 11:19 AM** [mentor] Dr. Paul confirmed, and recommended **ESMFold
(ESMFold2) and the ESM Protein Atlas**, attaching the original paper. This is
the origin of the ESMFold comparison listed as future work: ESMFold predicts
structure without multiple sequence alignments, so it directly tests the
alignment-scarcity explanation for a viral deficit.

**Aug 20, 2:49 to 2:52 PM** [mentor] Time confirmed.

**Aug 20, 3:00 PM** [mentor] **Zoom meeting held with Dr. Paul.**

**Aug 20** [code] Tidied the codebase and removed a duplicated disorder helper.

**Aug 25, 3:12 PM** [mentor] Update sent with the repository link, noting the
work was close to done and that the setup script, written instructions for the
conda environment, and the methods section would follow after some cleanup.

**Aug 25, 3:50 PM** [mentor] **Meeting missed.** Dr. Paul had a meeting run
over and did not join; rescheduled to the following Tuesday at 3 PM.

**Aug 25** [code] Moved fragment exclusion to selection time, so polyprotein
entries are kept out of the dataset rather than filtered from results. Added
one-command environment setup and the three-panel comparison figure.

**Aug 27** [code] Shipped ready-made 250 and 1000 protein registries so the
repository runs immediately after cloning.

**Aug 30, 4:02 PM** [mentor] Reschedule confirmed.

## September 2026

**Sep 1, 2:28 PM** [mentor] **Meeting cancelled.** Town-wide power outage;
proposed the same time the following week. Dr. Paul agreed at 2:58 PM.

**Sep 7, 1:02 PM** [mentor] Out of town, proposed Tuesday the 15th at 3 PM.

**Sep 8, 12:35 PM** [mentor] Dr. Paul confirmed the 15th.

**Sep 15, 3:00 PM** [mentor] **Zoom meeting held with Dr. Paul.** Two
attachments received afterwards at 3:29 PM.

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
was being scored against it. Thirty-three proteins were affected, every one
viral. Fixed by selecting the model that actually contains the crystallised
chain.

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
Verified the whole pipeline from a clean clone with no cache.

---

## How the headline number moved

Worth keeping visible, because the story of this project is the correction:

| date | set | viral vs cellular median TM | p |
|---|---|---|---|
| Jun 26 | 56 proteins, unfiltered | 0.88 vs 0.96 | 0.0007 |
| Jul 20 | 79 proteins, coverage-filtered | 0.95 vs 0.965 | 0.052 |
| Sep 22 | 250 proteins, validated selection | 0.927 vs 0.970 | 1.3e-08 |

The June figure was inflated by fragment artifacts. The July figure removed
them but on a small set, and could not demonstrate a difference. The September
figure is on a set three times larger with the artifacts excluded at source,
and it does.

## Reading shared by Dr. Paul

- **Jul 3** Foldseek-based phage genome annotation, outperforming HMMER
  (Nucleic Acids Research).
- **Aug 19** ESMFold2 and the ESM Protein Atlas.
- Phold, read and discussed in the Jul 20 report.

---

## Where the result stands

| dataset version | mismatches | analysed | is_viral p |
|---|---|---|---|
| original | 44 (39 viral) | 206 | 2.8e-07 |
| after model-selection fix | 17 (12 viral) | 221 | 5.2e-07 |
| after coverage-validated selection | **4** | **233** | **2.6e-06** |

Viral proteins are predicted less accurately: median TM-score 0.927 against
0.970, p = 1.3e-08. Both viral origin (p = 2.6e-06) and disorder (p = 1.8e-06)
predict accuracy independently, and the two are not confounded.

The finding held across three rebuilds of the dataset, each after fixing a
defect that penalised the viral side almost exclusively. Each fix should have
shrunk the gap if the gap were an artifact. It did not move.

## Effort

Measured, not estimated: **26 commits across 18 distinct working days**, 3,452
lines of Python in 8 files, spanning 20 June to 30 September. About 32 messages
in the mentor thread. **Five meetings held** (Jun 2 with Dr. Paul, Jul 8 by
Zoom, Aug 4 with Ms. Copice, Aug 20 by Zoom, Sep 15 by Zoom) and two lost, one
to Dr. Paul's schedule on Aug 25 and one to a power outage on Sep 1.

One constraint worth recording: through July the work ran alongside a 9 to 5
at BWSI, so development and meetings were evenings and weekends.

The hours below are an **estimate**, not a time log. The commit days, message
counts and meeting counts are measured; the hours attached to them are
reconstructed and should be corrected where memory says otherwise.

| Activity | Basis | Estimated hours |
|---|---|---|
| Development and debugging | 18 active days at 2 to 4 hours | 36 to 72 |
| Background reading | AlphaFold, TM-score, disorder prediction, statistics, plus the Foldseek, ESMFold and Phold papers | 10 to 15 |
| Correspondence | ~32 messages, about half composed | 6 to 8 |
| Writing | methods drafts, project brief, slides | 8 to 12 |
| Meetings and preparation | 5 held, with prep and follow-up | 6 to 8 |
| **Total** | | **66 to 115** |

A reasonable single figure to quote is **about 90 hours**. Pipeline runs take
roughly an hour each but are unattended and not counted.

The softest assumption is the 2 to 4 hours per active development day; that
line alone moves the total by more than 30 hours, so adjust it first.

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
- Draft paper sections are not in this repository yet. Methods is drafted;
  introduction, results and discussion are not.
