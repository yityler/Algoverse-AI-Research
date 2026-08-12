# Draws every question's confidence timelines as one contact sheet.
#   OUT_DIR=/path/to/pkls python results/aime25/plot_timelines.py
# One panel per question: each line is a trace's sliding-window confidence over
# its own life, coloured by how it ended. The blue band is the bar's range from
# armed to final.
import os, re, glob, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")
DATASET = os.environ.get("DATASET", "aime25")
PNG = os.environ.get("PNG", "confidence_timelines.png")

COLORS = {"correct": "forestgreen", "wrong": "crimson",
          "cut": "0.6", "truncated": "darkkhaki", "abandoned": "steelblue"}

runs = sorted(glob.glob(f"{OUT_DIR}/*.pkl"),
              key=lambda f: int(re.search(r"q(\d+)_", f).group(1)))
if not runs:
    raise SystemExit(f"no pkls in {OUT_DIR}")

cols = 5
rows = -(-len(runs) // cols)
fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 2.6 * rows), sharey=False)
axes = np.atleast_1d(axes).ravel()

for ax, path in zip(axes, runs):
    r = pickle.load(open(path, "rb"))
    gt, cfg = str(r["gt"]), r["config"]
    W = cfg["WINDOW"]
    v = r["voting"]["majority"]
    ans = str(v[0] if isinstance(v, (list, tuple)) else v)
    ok = ans.strip() == gt

    for t in r["traces"]:
        confs = t["confs"]
        if not confs:
            continue
        step = max(1, len(confs) // 400)          # keep the file small
        x = (np.arange(len(confs)) + W)[::step]
        y = np.asarray(confs)[::step]
        st = t["status"]
        if st == "finished":
            kind = "correct" if str(t["answer"]).strip() == gt else "wrong"
        elif st == "stopped":
            kind = "cut"
        elif st == "abandoned":
            kind = "abandoned"
        else:
            kind = "truncated"
        ax.plot(x, y, lw=0.8, alpha=0.85, color=COLORS[kind])

    lh = r.get("line_history") or []
    if lh:
        lo, hi = min(e["line"] for e in lh), max(e["line"] for e in lh)
        ax.axhspan(lo, hi, color="tab:blue", alpha=0.10)
        ax.axhline(lh[-1]["line"], color="tab:blue", ls="--", lw=0.9)

    ax.set_title(f"Q{r['qid']}  gt {gt}  {'OK' if ok else 'WRONG (%s)' % ans[:6]}"
                 f"\n{r['tokens']/1e3:.0f}k tokens",
                 fontsize=9, color="black" if ok else "crimson")
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2)

for ax in axes[len(runs):]:
    ax.axis("off")

handles = [Line2D([], [], color=c, lw=2, label=l) for l, c in
           [("finished correct", COLORS["correct"]), ("finished wrong", COLORS["wrong"]),
            ("cut at the bar", COLORS["cut"]), ("truncated at the cap", COLORS["truncated"]),
            ("drained when the run closed", COLORS["abandoned"])]]
handles.append(Line2D([], [], color="tab:blue", ls="--", lw=1.2, label="bar (band = armed to final)"))
fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=9, frameon=False)
fig.suptitle(f"PeerConf-low on {DATASET.upper()}: sliding-window confidence of every trace, "
             f"all {len(runs)} questions", fontsize=13)
fig.tight_layout(rect=[0, 0.035, 1, 0.975])
fig.savefig(PNG, dpi=110)
print("wrote", PNG)
