# AlphaFold viral vs cellular accuracy study

Does AlphaFold2 predict viral protein structures less accurately than human ones?
This project answers that by taking proteins whose real structure has been solved
experimentally, downloading AlphaFold's prediction for each one, measuring how
closely they match, and comparing the two groups.

---

## Installing it

**On NixOS, skip to [the NixOS section](#installing-it-on-nixos).** The conda
installer below does not work there, for reasons explained in that section.

### What you need first

A Mac or Linux computer, about 5 GB of free disk space, and an internet
connection. You do not need to install Python or conda yourself, and you do not
need administrator or sudo access. The installer handles all of it.

### The three commands

Open a terminal and run these:

    git clone https://github.com/2008wbbv/alphafoldstudy.git
    cd alphafoldstudy
    bash setup_env.sh

That is the entire installation. It takes five to fifteen minutes, and most of
that is downloading one large package (PyTorch).

### What the installer is actually doing

It runs four steps and prints each one as it goes.

**Step 1, finding conda.** Conda is the tool that manages scientific Python
packages. If your computer already has it, the installer uses it. If not, the
installer downloads Miniconda (a small version of it) and installs it for you.
Nothing is installed system-wide and your shell settings are left alone.

**Step 2, building the environment.** An environment is a private, self-contained
folder holding a specific version of Python and the ten packages this project
needs. Keeping them separate means this project cannot break anything else on
your computer, and nothing else can break this project. The list of packages
lives in `environment.yml`.

**Step 3, checking it worked.** The installer imports all ten packages and prints
a version number for each. If anything failed, it says which one.

**Step 4, the structure cache.** Skipped unless you ask for it. See the cluster
section below.

### Where everything gets put

| What | Where it goes |
|---|---|
| Miniconda | `~/miniconda3` (only if you did not already have conda) |
| The environment and its packages | `~/miniconda3/envs/alphafold-study` |
| Downloaded package files | `~/miniconda3/pkgs` |
| Protein structures downloaded by the study | `data/` inside the project folder |
| Results, figures and statistics | `results/` inside the project folder |

To put conda somewhere else, for example because your home folder is small or is
on a shared cluster with a size limit, set one variable before installing:

    export CONDA_ROOT=/somewhere/with/space/miniconda3
    bash setup_env.sh

Everything then goes under that path instead.

### Turning it on, every time

The installer deliberately does not edit your shell startup files, so conda is
not switched on automatically. This is on purpose: it means the project cannot
interfere with anything else, which matters on a shared computer or a cluster.

The cost is that each new terminal window needs these two lines first:

    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate alphafold-study

You will know it worked because your prompt changes to start with
`(alphafold-study)`.

If you would rather have it always on, add that first line to your `~/.bashrc`.

---

## Installing it on NixOS

### The two commands

    bash setup_nixos.sh
    bash run_nixos.sh

That is all. The first command takes ten to twenty minutes, most of it building
the sandbox and downloading PyTorch. The second runs the study.

### Why NixOS needs its own path

NixOS does not have the usual Linux folder layout. There is no `/usr/lib`, and
crucially no `/lib64/ld-linux-x86-64.so.2`, which is the small program every
normal Linux binary calls to start itself.

Almost every scientific Python package (numpy, scipy, matplotlib, PyTorch) is
distributed as a prebuilt binary compiled on a normal distribution. On NixOS
those binaries cannot start, and the error is famously confusing: it says
`No such file or directory` about a file that is clearly right there. It means
the loader is missing, not the file.

So `setup_env.sh` is no good here. Miniconda's own installer is a binary with
the same problem, and so is everything it would install.

`setup_nixos.sh` fixes this with `nix-shell`, which builds a sandbox containing
a conventional folder layout. Inside it, ordinary Python packages work normally.
Your actual system is untouched: nothing is installed outside the project
folder, no root access is needed, and your `configuration.nix` is not modified.

### What the installer does

1. **Checks the host** and creates `data/`, `results/` and `logs/`.
2. **Builds the sandbox** from `nix/fhs.nix`. Slow the first time, cached after.
3. **Creates a venv** at `.venv` and installs everything into it.
4. **Verifies** by importing all eleven packages and printing each version.

Step 3 installs CPU PyTorch first, from PyTorch's own package index. This is
deliberate: metapredict requires PyTorch, and the default one on PyPI is the
CUDA build, which is several gigabytes and completely useless here since nothing
in this project uses a GPU. Installing the CPU build first satisfies the
requirement so pip never reaches for the big one.

### Where everything goes

| What | Where |
|---|---|
| The sandbox | the Nix store, shared and cached |
| Python packages | `.venv/` inside the project folder |
| Structures, results, logs | `data/`, `results/`, `logs/` as usual |

To remove it all, delete `.venv` and run `nix-collect-garbage`.

### Useful variations

    bash setup_nixos.sh --recreate    rebuild the venv from scratch
    bash setup_nixos.sh --download    also pre-download every structure

    bash run_nixos.sh --registry proteins_1000.csv   the 1000-protein set
    bash run_nixos.sh src/compare_metrics.py         any other script

If your system uses flakes and has no `<nixpkgs>` on `NIX_PATH`, the script
notices and pins a nixpkgs release itself, so it works either way.

To poke around by hand:

    nix-shell nix/fhs.nix
    source .venv/bin/activate

---

## Running it

On NixOS use `bash run_nixos.sh` instead of the commands below; everything else
on this page applies unchanged.

Run everything from the project folder, not from inside `src/`.

    python src/af_study.py

This downloads each protein structure into `data/`, compares every AlphaFold
prediction against its experimental structure, runs the statistics, and writes
everything into `results/`.

It is safe to stop it and start it again. Structures already downloaded are
reused rather than fetched twice, so restarting picks up roughly where it left
off.

### What you get in results/

| File | What it is |
|---|---|
| `metrics.csv` | One row per protein: accuracy scores, confidence, disorder, coverage |
| `per_residue.csv` | One row per individual amino acid, with its local error |
| `stats.txt` | All statistical tests in readable form |
| `regression.txt` | The analysis separating viral origin from disorder |
| `per_residue_stats.txt` | Correlations at the individual amino acid level |

### The graphs

Five figures are generated. Each one answers a specific question.

| Figure | Question it answers |
|---|---|
| `tm_boxplot.png` | Are viral proteins predicted less accurately than human ones? |
| `plddt_vs_tm.png` | Does AlphaFold's confidence track how accurate it actually was? |
| `disorder_vs_tm.png` | Do proteins with more floppy regions get predicted worse? |
| `compare_metrics.png` | All three measures side by side, with a significance test on each |
| `per_residue_disorder_hexbin.png` | Zoomed in to single amino acids: does local disorder predict local error? |

`plddt_vs_tm.png` is the one to point at when explaining the coverage filter.
Proteins flagged as sequence mismatches are drawn as x markers, and they sit in
a telling place: high confidence but low accuracy. AlphaFold was sure and
correct about a region that was never the one being compared. A genuine
prediction failure looks the opposite, low confidence and low accuracy.

Planned but not yet built:

- A coverage histogram, showing the split between real comparisons and
  sequence mismatches.
- A per-disorder-bin accuracy chart, showing accuracy falling as disorder rises.
- An ESMFold comparison, if that arm of the project goes ahead.

### The other commands

    python src/compare_metrics.py    # box chart plus Mann-Whitney tests
    python src/extra_stats.py        # extra robustness tests, appended to stats.txt
    python src/make_captions.py      # figure captions built from the real numbers
    python src/make_protein_lists.py # rebuild the protein lists from scratch

---

## Results so far

A full 250-protein run is committed in [`results_250/`](results_250/), so you
can look at the figures and tables without running anything. All 250 proteins
processed without error; 44 were flagged as sequence mismatches, leaving 206.

| | viral | cellular |
|---|---|---|
| median TM-score | 0.912 | 0.968 |
| median pLDDT | 79.1 | 86.8 |
| flagged as mismatches | 39 of 125 | 5 of 125 |

Viral proteins are predicted less accurately, and the difference survives
controlling for disorder and coverage (regression p = 2.8e-07). This **reverses
the earlier 79-protein pilot**, where disorder carried the effect and viral
origin did not. The larger run says the opposite: viral origin is significant
and disorder is not (p = 0.073). See `results_250/README.md`.

---

## The protein lists

Two lists come with the project, so there is nothing to build before your first
run.

| File | Proteins | Viral | Cellular |
|---|---|---|---|
| `proteins_250.csv` | 250 | 125 | 125 |
| `proteins_1000.csv` | 1000 | 445 | 555 |

`proteins.csv` is a copy of the 250 list and is what runs by default. To use the
bigger one:

    python src/af_study.py --registry proteins_1000.csv

Both were pulled straight from the RCSB Protein Data Bank, keeping one structure
per protein, only structures resolved to 3.0 angstroms or better, only proteins
between 50 and 600 amino acids, and only ones that actually have an AlphaFold
model. Polyproteins are excluded, for the reason explained at the bottom of this
page.

The 250 list is evenly balanced and is the better one for the actual comparison.
The 1000 list is uneven because 445 is simply how many viral proteins qualify;
there is no larger balanced set available.

---

## Running it on a computing cluster

The one thing that matters: **cluster compute nodes usually have no internet
access.** So the packages and the protein structures both have to be downloaded
first, on the login node, where there is internet. The jobs then read from disk.

On the login node:

    export CONDA_ROOT=/scratch/$USER/miniconda3     # somewhere with space
    bash setup_env.sh --download

The `--download` flag adds a step: after installing, it fetches every protein
structure into `data/`. This is what lets the jobs run offline.

Then create the job files:

    conda activate alphafold-study
    python src/make_batches.py

That writes `jobs/batch_01.sh` and so on, 250 proteins per job. Each batch gets a
proportional mix of viral and cellular proteins, which matters because a batch
containing only one group cannot run the comparison the study is about.

Before submitting, open each `jobs/batch_NN.sh` and fill in three things:

1. Your account and partition, which your cluster's documentation will name:

        #SBATCH --account=YOUR_ACCOUNT
        #SBATCH --partition=YOUR_PARTITION

2. The two activation lines, with the path you used above:

        source /scratch/$USER/miniconda3/etc/profile.d/conda.sh
        conda activate alphafold-study

3. Time, memory and CPU count, if the defaults of 12 hours, 16 GB and 4 CPUs do
   not suit your cluster.

Then submit, and merge the outputs when the jobs finish:

    sbatch jobs/batch_01.sh
    python src/merge_results.py

Merging only stitches the tables back together; it runs no statistics, and the
`stats.txt` inside each batch folder describes that batch alone. To get the
statistics for the whole set, point the analysis at the merged table:

    python src/compare_metrics.py --metrics results/combined_metrics.csv \
        --out-dir results/combined
    python src/extra_stats.py --metrics results/combined_metrics.csv \
        --stats results/combined_stats.txt

`merge_results.py` prints these two commands when it finishes, so there is
nothing to remember.

---

## What the project actually measures

Each protein gets compared on four things:

- **TM-score**, from 0 to 1, for how closely the predicted shape matches the real
  one. Above 0.5 means the same overall fold.
- **RMSD**, the average distance in angstroms between matched atoms.
- **pLDDT**, AlphaFold's own confidence, from 0 to 100.
- **Disorder**, the fraction of the protein predicted to have no fixed shape.

### Why polyproteins are excluded

Many viruses make one long protein and then cut it into smaller working pieces.
Every piece keeps the identifier of the original long protein. AlphaFold splits
very long sequences into chunks and publishes only the first chunk, which often
does not contain the piece that was experimentally solved.

Comparing those two gives a near-zero score, but nothing went wrong with the
prediction: the wrong stretch of sequence was compared. Because polyproteins are
a viral strategy and are rare in humans, this affects one group far more than the
other, and it will invent a difference between the groups that is not real.

The project handles this twice. Proteins whose full sequence is too long for
AlphaFold to publish in one piece are excluded when the list is built. Then,
during the analysis, a coverage check measures how much of the real protein
actually appears in the model and flags anything below 80 percent. Every result
is reported both with and without those flagged proteins.

---

## If something goes wrong

Full troubleshooting is in [INSTALL.txt](INSTALL.txt). The three most common:

**`conda: command not found`** after installing. Run the `source` line from the
"Turning it on" section above.

**`CondaToSNonInteractiveError`.** Recent conda versions require accepting
Anaconda's terms before installing anything. `setup_env.sh` does this for you, so
you only hit it if you ran conda by hand. The fix is printed in the error.

**`No space left on device`.** The environment needs about 5 GB. Reinstall
somewhere larger using `CONDA_ROOT` as shown above.

**`No such file or directory`, on NixOS, about a file that plainly exists.**
That is the missing dynamic loader described in the NixOS section. It means
something ran outside the sandbox. Use `bash run_nixos.sh`, or enter the sandbox
first with `nix-shell nix/fhs.nix`.

---

## Project layout

    src/                    all the code
      build_registry.py     picks proteins from RCSB, one at a time
      make_protein_lists.py picks proteins in bulk, much faster
      af_study.py           the main study
      compare_metrics.py    box chart and group comparison
      extra_stats.py        additional statistical tests
      make_captions.py      figure captions
      make_batches.py       splits the list into cluster jobs
      merge_results.py      recombines cluster job output
    jobs/                   generated cluster job files
    nix/fhs.nix             FHS sandbox definition, for NixOS
    environment.yml         package list for the conda install
    requirements.txt        package list for the venv install (NixOS)
    setup_env.sh            the installer, Mac and normal Linux
    setup_nixos.sh          the installer, NixOS
    run_nixos.sh            runs the study on NixOS
    INSTALL.txt             detailed setup and troubleshooting
    proteins_250.csv        ready-made 250-protein list
    proteins_1000.csv       ready-made 1000-protein list
    proteins.csv            the list currently in use

`data/`, `results/` and `logs/` are created when you run the study and are not
stored in the repository.
