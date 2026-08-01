# ============ CELL 3 — CONFIDENCE TIMELINES (run any time after races) ============
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt

OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")

QIDS = "all"     # which questions to draw: "all" = every saved run,
                 # or a specific set like [6] or [6, 9, 12]

def qid_of(fname):
    m = re.match(r"q(\d+)_", fname)
    return int(m.group(1)) if m else None

runs = sorted((f for f in os.listdir(OUT_DIR) if f.endswith(".pkl")),
              key=lambda f: (qid_of(f) is None, qid_of(f)))
print("saved runs:", runs)
if QIDS != "all":
    wanted = set(QIDS)
    runs = [f for f in runs if qid_of(f) in wanted]
if not runs:
    raise SystemExit("No saved runs match QIDS — run CELL 2 first.")

def draw_timeline(fname):
    with open(f"{OUT_DIR}/{fname}", "rb") as f:
        r = pickle.load(f)

    qid, gt = r["qid"], str(r["gt"])
    cfg     = r["config"]
    WINDOW  = cfg["WINDOW"]

    def is_right(ans):
        return ans is not None and str(ans).strip() == gt

    # the wrong majority (most common wrong answer among finishers) gets its own color
    finished = [t for t in r["traces"] if t["status"] == "finished" and t["answer"] is not None]
    wrong_counts = {}
    for t in finished:
        if not is_right(t["answer"]):
            wrong_counts[str(t["answer"])] = wrong_counts.get(str(t["answer"]), 0) + 1
    wrong_majority = max(wrong_counts, key=wrong_counts.get) if wrong_counts else None

    n_right = sum(1 for t in finished if is_right(t["answer"]))
    n_wmaj  = sum(1 for t in finished if str(t["answer"]) == wrong_majority) if wrong_majority else 0

    fig, ax = plt.subplots(figsize=(16, 9))
    seen_labels = set()
    def label_once(lab):
        if lab in seen_labels: return None
        seen_labels.add(lab); return lab

    for t in r["traces"]:
        confs = t["confs"]
        if not confs: continue
        x = np.arange(len(confs)) + WINDOW         # confs[0] = the first full window
        step = max(1, len(confs) // 2000)          # downsample for the figure
        xs, ys = x[::step], np.asarray(confs)[::step]

        if t["status"] == "stopped":               # cut at the line
            ax.plot(xs, ys, color="gray", lw=1.0, alpha=0.7,
                    label=label_once("cut at the line"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=1.8,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            ax.plot(x[-1], confs[-1], "o", color="forestgreen", ms=5)
        elif t["status"] == "finished" and wrong_majority and str(t["answer"]) == wrong_majority:
            ax.plot(xs, ys, color="crimson", lw=1.8,
                    label=label_once(f"wrong majority = {wrong_majority} (n={n_wmaj})"))
            ax.plot(x[-1], confs[-1], "o", color="crimson", ms=5)
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="lightcoral", lw=1.2, alpha=0.85,
                    label=label_once("other wrong answers"))
            ax.plot(x[-1], confs[-1], "o", color="lightcoral", ms=4)
        else:                                      # truncated / abandoned — no answer
            ax.plot(xs, ys, color="darkkhaki", lw=1.2, ls="--", alpha=0.9,
                    label=label_once("no answer (truncated/abandoned)"))
            ax.plot(x[-1], confs[-1], "o", color="darkkhaki", ms=4)

    # the belt line: where it went live and where it ended, with the sag band between
    lh = r.get("line_history", [])
    if lh:
        first, last = lh[0]["line"], lh[-1]["line"]
        ax.axhline(first, color="tab:blue", ls="--", lw=1.3,
                   label=f"belt line (keep top {cfg['LINE_TOP']:.0%}, live)")
        ax.axhline(last, color="tab:blue", ls="--", lw=1.3)
        ax.axhspan(min(first, last), max(first, last), color="tab:blue", alpha=0.06)
        ax.annotate(f"line goes live: {first:.2f}", xy=(1.0, first),
                    xycoords=("axes fraction", "data"), xytext=(-8, 6),
                    textcoords="offset points", ha="right", color="tab:blue")
        ax.annotate(f"line at race end: {last:.2f}", xy=(1.0, last),
                    xycoords=("axes fraction", "data"), xytext=(-8, -14),
                    textcoords="offset points", ha="right", color="tab:blue")

    ax.set_xlabel(f"tokens generated (each point = sliding-window average: "
                  f"the confidence of the previous {WINDOW} tokens)")
    ax.set_ylabel("sliding-window confidence")
    ax.set_title(
        f"PeerConf, AIME25 Q{qid}: sliding-window confidence of all {len(r['traces'])} traces "
        f"(window = {WINDOW} tokens, ground truth {gt})\n"
        f"cut = {cfg['DWELL_TOKENS']} consecutive tokens below the line "
        f"({WINDOW} x {cfg['DWELL_TOKENS']}: window x dwell) | model: {cfg['MODEL']}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid}_confidence_timeline.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
