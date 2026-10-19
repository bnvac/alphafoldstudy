#!/usr/bin/env python3
"""esmfold_compare.py

The mechanism test. AlphaFold2 predicts structure from a multiple sequence
alignment, and the study's working hypothesis is that viral proteins are
predicted worse because they have fewer detectable relatives to align against.
ESMFold predicts structure from a protein language model and uses no alignment
at all. Running the same proteins through both tests whether the viral deficit
depends on the alignment step:

  gap the same under ESMFold   the deficit is not specific to alignments
  gap smaller under ESMFold    alignments are where AlphaFold2 loses ground
  gap larger under ESMFold     alignments partly rescue AlphaFold2 on viral
                               proteins, and the language model is weaker still

The key statistic is the interaction: whether AlphaFold2's advantage over
ESMFold, measured per protein, differs between viral and cellular proteins.

Each crystallised construct is folded through the public ESM Atlas API, which
serves ESMFold v1 and accepts sequences up to 400 residues. Longer constructs
are skipped, and every comparison is then made on the proteins both programs
scored, so neither side is judged on a set the other never saw.

Reads  results/metrics.csv          the AlphaFold2 run
Writes data/ESM-<pdb>_<chain>.pdb   ESMFold models, reused on later runs
       results/esmfold_metrics.csv  per-protein AlphaFold2 and ESMFold scores
       results/esmfold_stats.txt    the head-to-head statistics
       results/esmfold_compare.png  paired scatter and grouped boxes

Run with:  python src/esmfold_compare.py
           python src/esmfold_compare.py --metrics results_250/metrics.csv
"""

import argparse
import csv
import json
import os
import sys
import time

import numpy as np
import requests
from scipy.stats import mannwhitneyu, spearmanr, wilcoxon

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Structure loading and alignment are imported so ESMFold models are scored by
# exactly the code that scored AlphaFold2. Importing af_study also runs its
# dependency bootstrap.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from af_study import (  # noqa: E402
    experimental_prefix, load_chain, local_structure_path)
from tmtools import tm_align  # noqa: E402

CONFIG = {
    "esm_api_url": "https://api.esmatlas.com/foldSequence/v1/pdb/",
    "rcsb_graphql_url": "https://data.rcsb.org/graphql",
    # Above this the API answers HTTP 413. Measured, not documented.
    "esm_max_length": 400,
    "data_dir": "data",
    "sequence_cache": os.path.join("data", "esm_sequences.json"),
    "request_sleep": 0.5,
    "retries": 3,
    "timeout": 120,
}

COLORS = {"viral": "#d1495b", "cellular": "#2077C9"}
GROUPS = ["viral", "cellular"]
INK, INK_MUTED, GRID = "#1B2430", "#5A6675", "#DFE4EA"

FIELDS = ["name", "type", "pdb_id", "pdb_chain", "uniprot", "construct_len",
          "disorder_frac", "af_tm", "esm_tm", "af_plddt", "esm_plddt",
          "esm_rmsd", "esm_status"]


def load_usable(path):
    """Rows the AlphaFold2 analysis kept: processed, covered, well resolved."""
    rows = []
    with open(path, newline="") as handle:
        for r in csv.DictReader(handle):
            if r.get("status") != "ok":
                continue
            if r.get("fragment_flag") == "True" or r.get("missing_flag") == "True":
                continue
            if r.get("tm_score") in (None, "", "NA"):
                continue
            rows.append(r)
    return rows


def construct_sequences(rows):
    """Map (pdb_id, chain) -> deposited construct sequence, cached on disk.

    The construct sequence (SEQRES) is folded rather than the resolved residues,
    because the resolved chain has gaps wherever density was missing, and
    folding a sequence with residues deleted would join pieces of the protein
    that are not adjacent in reality.
    """
    cache = {}
    if os.path.exists(CONFIG["sequence_cache"]):
        with open(CONFIG["sequence_cache"]) as handle:
            cache = json.load(handle)

    wanted = sorted({r["pdb_id"] for r in rows
                     if "{0}|{1}".format(r["pdb_id"], r["pdb_chain"]) not in cache})
    for start in range(0, len(wanted), 100):
        ids = ",".join('"{0}"'.format(x) for x in wanted[start:start + 100])
        query = ("{ entries(entry_ids: [%s]) { rcsb_id polymer_entities { "
                 "rcsb_polymer_entity_container_identifiers { auth_asym_ids } "
                 "entity_poly { pdbx_seq_one_letter_code_can } } } }" % ids)
        try:
            resp = requests.post(CONFIG["rcsb_graphql_url"], json={"query": query},
                                 timeout=CONFIG["timeout"])
            entries = (resp.json().get("data") or {}).get("entries") or []
        except Exception as exc:
            print("  sequence batch at {0} failed: {1}".format(start, exc))
            continue
        for entry in entries:
            for entity in entry.get("polymer_entities") or []:
                seq = "".join((entity["entity_poly"].get("pdbx_seq_one_letter_code_can")
                               or "").split())
                ids_ = entity["rcsb_polymer_entity_container_identifiers"]
                for chain in ids_.get("auth_asym_ids") or []:
                    cache["{0}|{1}".format(entry["rcsb_id"], chain)] = seq

    os.makedirs(CONFIG["data_dir"], exist_ok=True)
    with open(CONFIG["sequence_cache"], "w") as handle:
        json.dump(cache, handle)
    return cache


def esm_model_path(pdb_id, chain):
    return os.path.join(CONFIG["data_dir"], "ESM-{0}_{1}.pdb".format(pdb_id, chain))


def fold(sequence, out_path):
    """Fold one sequence through the ESM Atlas API. Return ok/skip/fail."""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return "skip"
    for attempt in range(CONFIG["retries"]):
        try:
            resp = requests.post(CONFIG["esm_api_url"], data=sequence,
                                 timeout=CONFIG["timeout"])
            if resp.status_code == 200 and resp.text.lstrip().startswith(("HEADER", "ATOM", "REMARK", "MODEL", "PARENT")):
                with open(out_path, "w") as handle:
                    handle.write(resp.text)
                time.sleep(CONFIG["request_sleep"])
                return "ok"
            if resp.status_code == 413:
                return "fail"  # too long; retrying cannot help
        except Exception as exc:
            print("    fold attempt {0} failed: {1}".format(attempt + 1, exc))
        time.sleep(2 ** (attempt + 1))
    return "fail"


def score(pdb_id, chain, model_path):
    """TM-score and RMSD of a model against the crystal, plus mean pLDDT.

    TM-score is normalised by the crystal chain, matching how AlphaFold2 was
    scored, so the two numbers measure the same thing.
    """
    exp_path = local_structure_path(experimental_prefix(pdb_id))
    if exp_path is None:
        return None
    _, exp_coords, exp_seq = load_chain(exp_path, chain)
    model_chain, model_coords, model_seq = load_chain(model_path, "A")
    result = tm_align(exp_coords, model_coords, exp_seq, model_seq)
    # ESMFold writes pLDDT on a 0 to 1 scale; AlphaFold2 uses 0 to 100.
    plddt = [atom.get_bfactor() for res in model_chain
             for atom in res if atom.get_id() == "CA"]
    mean_plddt = float(np.mean(plddt)) * 100.0 if plddt else None
    return float(result.tm_norm_chain1), float(result.rmsd), mean_plddt


def run(rows, sequences):
    """Fold and score every usable protein, returning one dict per protein."""
    out = []
    print("\n=== Folding with ESMFold ({0} proteins) ===".format(len(rows)))
    for r in rows:
        seq = sequences.get("{0}|{1}".format(r["pdb_id"], r["pdb_chain"]), "")
        rec = {"name": r["name"], "type": r["type"], "pdb_id": r["pdb_id"],
               "pdb_chain": r["pdb_chain"], "uniprot": r["uniprot"],
               "construct_len": len(seq), "disorder_frac": r.get("disorder_frac"),
               "af_tm": float(r["tm_score"]), "af_plddt": r.get("mean_plddt"),
               "esm_tm": None, "esm_plddt": None, "esm_rmsd": None, "esm_status": "ok"}
        if not seq:
            rec["esm_status"] = "no construct sequence"
        elif len(seq) > CONFIG["esm_max_length"]:
            rec["esm_status"] = "over {0} residues".format(CONFIG["esm_max_length"])
        else:
            path = esm_model_path(r["pdb_id"], r["pdb_chain"])
            state = fold(seq, path)
            if state == "fail":
                rec["esm_status"] = "fold failed"
            else:
                try:
                    tm, rmsd, plddt = score(r["pdb_id"], r["pdb_chain"], path)
                    rec.update(esm_tm=tm, esm_rmsd=rmsd, esm_plddt=plddt)
                except Exception as exc:
                    rec["esm_status"] = "scoring failed: {0}".format(exc)
        if rec["esm_status"] == "ok":
            print("  {0:<32} AF2={1:.3f}  ESM={2:.3f}".format(
                r["name"][:32], rec["af_tm"], rec["esm_tm"]))
        else:
            print("  {0:<32} skipped: {1}".format(r["name"][:32], rec["esm_status"]))
        out.append(rec)
    return out


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rank_biserial(u, n1, n2):
    return 2.0 * u / (n1 * n2) - 1.0


def stats(records, out_txt):
    """The head-to-head, on proteins both programs scored."""
    paired = [r for r in records if r["esm_status"] == "ok"]
    lines = []

    def emit(text=""):
        print(text)
        lines.append(text)

    def group(field, g):
        return np.array([r[field] for r in paired if r["type"] == g], dtype=float)

    def mwu_line(label, v, c):
        u, p = mannwhitneyu(v, c, alternative="two-sided")
        emit("  {0:<22} viral {1:.3f}  cellular {2:.3f}  p = {3:.3g}  r = {4:+.3f}".format(
            label, np.median(v), np.median(c), p, rank_biserial(u, len(v), len(c))))
        return p

    emit("ESMFold against AlphaFold2: is the viral deficit an alignment effect?")
    emit("ESMFold v1 via the ESM Atlas API. All comparisons use only the proteins")
    emit("both programs scored, so each is judged on the same set.")
    emit("")
    for g in GROUPS:
        allg = [r for r in records if r["type"] == g]
        okg = [r for r in allg if r["esm_status"] == "ok"]
        emit("  {0:<9} {1} of {2} scored by ESMFold".format(g, len(okg), len(allg)))
    skipped = {}
    for r in records:
        if r["esm_status"] != "ok":
            skipped[r["esm_status"]] = skipped.get(r["esm_status"], 0) + 1
    for reason, n in sorted(skipped.items()):
        emit("    skipped, {0}: {1}".format(reason, n))
    emit("")

    emit("1. The viral gap under each program (Mann-Whitney U, median TM-score)")
    p_af = mwu_line("AlphaFold2", group("af_tm", "viral"), group("af_tm", "cellular"))
    p_esm = mwu_line("ESMFold", group("esm_tm", "viral"), group("esm_tm", "cellular"))
    emit("")

    emit("2. AlphaFold2 against ESMFold on the same proteins (Wilcoxon signed-rank)")
    for g in GROUPS:
        af, esm = group("af_tm", g), group("esm_tm", g)
        _, p = wilcoxon(af, esm)
        emit("  {0:<9} AF2 median {1:.3f}, ESM median {2:.3f}, "
             "median AF2 advantage {3:+.3f}, p = {4:.3g}".format(
                 g, np.median(af), np.median(esm), np.median(af - esm), p))
    emit("")

    emit("3. THE KEY TEST: does AlphaFold2's advantage differ between groups?")
    emit("   Per protein, advantage = AF2 TM-score minus ESMFold TM-score.")
    dv = group("af_tm", "viral") - group("esm_tm", "viral")
    dc = group("af_tm", "cellular") - group("esm_tm", "cellular")
    u, p_int = mannwhitneyu(dv, dc, alternative="two-sided")
    emit("  median advantage: viral {0:+.3f}, cellular {1:+.3f}".format(
        np.median(dv), np.median(dc)))
    emit("  Mann-Whitney on the advantage: p = {0:.3g}, r = {1:+.3f}".format(
        p_int, rank_biserial(u, len(dv), len(dc))))
    gap_af = np.median(group("af_tm", "cellular")) - np.median(group("af_tm", "viral"))
    gap_esm = np.median(group("esm_tm", "cellular")) - np.median(group("esm_tm", "viral"))
    emit("  viral gap in median TM: AF2 {0:.3f}, ESMFold {1:.3f}".format(gap_af, gap_esm))
    emit("")

    emit("4. Regression, ESMFold TM-score ~ disorder + is_viral")
    try:
        import statsmodels.api as sm
        recs = [r for r in paired if _num(r["disorder_frac"]) is not None]
        y = np.array([r["esm_tm"] for r in recs])
        X = np.column_stack([[_num(r["disorder_frac"]) for r in recs],
                             [1.0 if r["type"] == "viral" else 0.0 for r in recs]])
        fit = sm.OLS(y, sm.add_constant(X)).fit()
        y_af = np.array([r["af_tm"] for r in recs])
        fit_af = sm.OLS(y_af, sm.add_constant(X)).fit()
        emit("  n = {0}".format(len(recs)))
        emit("  ESMFold    is_viral coef {0:+.4f}, p = {1:.3g};  disorder coef {2:+.4f}, p = {3:.3g}".format(
            fit.params[2], fit.pvalues[2], fit.params[1], fit.pvalues[1]))
        emit("  AlphaFold2 is_viral coef {0:+.4f}, p = {1:.3g};  disorder coef {2:+.4f}, p = {3:.3g}".format(
            fit_af.params[2], fit_af.pvalues[2], fit_af.params[1], fit_af.pvalues[1]))
        emit("  (same proteins and model for both, so the coefficients compare directly)")
    except Exception as exc:
        emit("  regression unavailable: {0}".format(exc))
    emit("")

    emit("5. Does ESMFold's own confidence track its error?")
    ep = [r for r in paired if r["esm_plddt"] is not None]
    rho, p = spearmanr([r["esm_plddt"] for r in ep], [r["esm_tm"] for r in ep])
    emit("  Spearman, ESMFold pLDDT vs TM-score: rho = {0:+.3f}, p = {1:.3g} (n = {2})".format(
        rho, p, len(ep)))
    emit("")

    emit("Reading")
    if p_esm < 0.05 and p_int >= 0.05:
        emit("  The viral gap appears under both programs and AlphaFold2's advantage")
        emit("  does not differ between groups. The deficit is therefore not specific")
        emit("  to AlphaFold2's alignment step; it follows the proteins, not the method.")
    elif p_int < 0.05 and np.median(dv) < np.median(dc):
        emit("  AlphaFold2 gains less over ESMFold on viral proteins than on cellular")
        emit("  ones. That is what alignment scarcity predicts: the alignment step is")
        emit("  where AlphaFold2 loses ground on viral proteins.")
    elif p_int < 0.05:
        emit("  AlphaFold2 gains more over ESMFold on viral proteins than on cellular")
        emit("  ones. Alignments partly rescue AlphaFold2 on viral proteins, and the")
        emit("  language model is weaker on them still.")
    else:
        emit("  Neither the ESMFold gap nor the interaction reaches significance, so")
        emit("  this test does not distinguish the explanations at this sample size.")
    emit("  This is a test of the alignment explanation, not a proof of mechanism:")
    emit("  ESMFold's language model was itself trained on sequence databases in")
    emit("  which viral proteins are under-represented.")

    with open(out_txt, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("Wrote {0}".format(out_txt))


def figure(records, out_png):
    """Paired scatter (AF2 vs ESMFold per protein) and grouped boxes."""
    paired = [r for r in records if r["esm_status"] == "ok"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0))

    for g in GROUPS:
        pts = [r for r in paired if r["type"] == g]
        ax1.scatter([r["esm_tm"] for r in pts], [r["af_tm"] for r in pts], s=24,
                    color=COLORS[g], alpha=.72, edgecolor="white", linewidth=.6,
                    label=g, zorder=3)
    ax1.plot([0, 1], [0, 1], color=INK_MUTED, linewidth=1, linestyle="--", zorder=2)
    ax1.set_xlim(0, 1.02)
    ax1.set_ylim(0, 1.02)
    ax1.set_xlabel("ESMFold TM-score (no alignment)", color=INK)
    ax1.set_ylabel("AlphaFold2 TM-score (uses alignment)", color=INK)
    # The reading key goes in the title: placed inside the axes it sat on top of
    # the viral points that matter most, the ones far above the diagonal.
    ax1.set_title("Per protein: above the line, AlphaFold2 did better",
                  color=INK, fontweight="semibold")
    ax1.legend(frameon=False, loc="lower right")

    data, pos, cols = [], [], []
    for i, (field, label) in enumerate([("af_tm", "AlphaFold2"), ("esm_tm", "ESMFold")]):
        for j, g in enumerate(GROUPS):
            data.append([r[field] for r in paired if r["type"] == g])
            pos.append(i * 3 + j + 1)
            cols.append(COLORS[g])
    bp = ax2.boxplot(data, positions=pos, widths=.7, showfliers=False, patch_artist=True,
                     medianprops={"color": INK, "linewidth": 1.6})
    for patch, c in zip(bp["boxes"], cols):
        patch.set_facecolor(c)
        patch.set_alpha(.22)
        patch.set_edgecolor(c)
    ax2.set_xticks([1.5, 4.5])
    ax2.set_xticklabels(["AlphaFold2", "ESMFold"], color=INK)
    ax2.set_ylabel("TM-score against the crystal structure", color=INK)
    ax2.set_title("Viral gap under each program", color=INK, fontweight="semibold")

    for ax in (ax1, ax2):
        ax.grid(color=GRID, linewidth=.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=INK_MUTED)

    fig.suptitle("Does the viral deficit depend on AlphaFold2's alignment step?",
                 color=INK, fontsize=13, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, .95])
    fig.savefig(out_png, dpi=200, facecolor="white")
    plt.close(fig)
    print("Wrote {0}".format(out_png))


def main():
    parser = argparse.ArgumentParser(description="ESMFold head-to-head with AlphaFold2.")
    parser.add_argument("--metrics", default=os.path.join("results", "metrics.csv"))
    parser.add_argument("--out-dir", default=None,
                        help="where to write outputs (default: alongside --metrics)")
    args = parser.parse_args()

    if not os.path.exists(args.metrics):
        print("No metrics table at {0}. Run af_study.py first.".format(args.metrics))
        return
    out_dir = args.out_dir or os.path.dirname(args.metrics) or "."
    os.makedirs(out_dir, exist_ok=True)

    rows = load_usable(args.metrics)
    print("Loaded {0} usable proteins from {1}.".format(len(rows), args.metrics))
    sequences = construct_sequences(rows)
    records = run(rows, sequences)

    out_csv = os.path.join(out_dir, "esmfold_metrics.csv")
    with open(out_csv, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow({k: ("" if r[k] is None else
                                 ("{0:.4f}".format(r[k]) if isinstance(r[k], float) else r[k]))
                             for k in FIELDS})
    print("Wrote {0}".format(out_csv))

    stats(records, os.path.join(out_dir, "esmfold_stats.txt"))
    figure(records, os.path.join(out_dir, "esmfold_compare.png"))


if __name__ == "__main__":
    main()
