# ============ CELL 3 — CONFIDENCE TIMELINES (run any time after CELL 2) ============
# Draws the game tape from saved runs: every trace's sliding-window confidence
# over its life, colored by outcome, with the frozen warmup bar. One figure per
# question. Pick which questions with QIDS below.
# Green = finished correct, red = the wrong majority, light red = other wrong
# answers, gray + X = cut at the bar, khaki dashed = truncated with no answer,
# steel dotted = drained when consensus closed the run. Thin lines = warmup
# traces (never judged), thick lines = the online wave.
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt

OUT_DIR = os.environ.get("OUT_DIR", "deepconf_out")

QIDS = "all"     # "all" = every saved run, or a set like [6] or [6, 9, 12]

DATASET = os.environ.get("DATASET", "aime25")   # draw one benchmark at a time: the
                                                # same question number is a different
                                                # question in each benchmark

def qid_of(fname):                           # non-aime25 runs are <dataset>_q<N>_...
    m = re.match(r"(?:\w+?_)?q(\d+)_deepconf_", fname)
    return int(m.group(1)) if m else None

def ds_of(fname):
    m = re.match(r"(?:(\w+?)_)?q\d+_deepconf_", fname)
    return (m.group(1) or "aime25") if m else None

runs = sorted((f for f in os.listdir(OUT_DIR)
               if f.endswith(".pkl") and ds_of(f) == DATASET), key=qid_of)
print(f"saved {DATASET} runs:", runs)
if QIDS != "all":
    runs = [f for f in runs if qid_of(f) in set(QIDS)]
if not runs:
    raise SystemExit("No saved runs match QIDS — run CELL 2 first.")

def draw_timeline(fname):
    with open(f"{OUT_DIR}/{fname}", "rb") as f:
        r = pickle.load(f)

    qid, gt = r["qid"], str(r["gt"])
    cfg     = r["config"]
    WINDOW  = cfg["WINDOW"]
    bar     = r.get("conf_bar", cfg.get("conf_bar"))

    def is_right(ans):
        return ans is not None and str(ans).strip() == gt

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
        lw = 1.0 if t.get("phase") == "warmup" else 1.8

        if t["status"] == "stopped":               # cut at the bar
            ax.plot(xs, ys, color="gray", lw=1.0, alpha=0.7,
                    label=label_once("cut at the bar"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=lw,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            ax.plot(x[-1], confs[-1], "o", color="forestgreen", ms=5)
        elif t["status"] == "finished" and wrong_majority and str(t["answer"]) == wrong_majority:
            ax.plot(xs, ys, color="crimson", lw=lw,
                    label=label_once(f"wrong majority = {wrong_majority} (n={n_wmaj})"))
            ax.plot(x[-1], confs[-1], "o", color="crimson", ms=5)
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="lightcoral", lw=max(lw - 0.6, 1.0), alpha=0.85,
                    label=label_once("other wrong answers"))
            ax.plot(x[-1], confs[-1], "o", color="lightcoral", ms=5)
        elif t["status"] == "abandoned":           # drained when consensus closed the run
            ax.plot(xs, ys, color="steelblue", lw=1.1, ls=":", alpha=0.8,
                    label=label_once("drained (consensus stop)"))
            ax.plot(x[-1], confs[-1], "s", color="steelblue", ms=4)
        else:                                      # truncated — cap or EOS, no answer
            ax.plot(xs, ys, color="darkkhaki", lw=1.2, ls="--", alpha=0.9,
                    label=label_once("no answer (truncated)"))
            ax.plot(x[-1], confs[-1], "o", color="darkkhaki", ms=4)

    if bar is not None:
        keep = cfg.get("CONFIDENCE_PERCENTILE", "?")
        # one line doing two jobs: it cuts the online wave, and a warmup trace
        # below it does not get to vote
        ax.axhline(bar, color="teal", ls="-.", lw=1.6,
                   label=f"frozen bar: cuts the online wave, and warmup must "
                         f"clear it to vote (top {keep}%)")
        ax.annotate(f"bar: {bar:.2f}", xy=(0.0, bar),
                    xycoords=("axes fraction", "data"), xytext=(8, 6),
                    textcoords="offset points", ha="left", color="teal")

    ax.set_xlabel(f"tokens generated (each point = sliding-window average: "
                  f"the confidence of the previous {WINDOW} tokens)")
    ax.set_ylabel("sliding-window confidence")
    ax.set_title(
        f"DeepConf, AIME25 Q{qid}: sliding-window confidence of all {len(r['traces'])} traces "
        f"(window = {WINDOW} tokens, ground truth {gt})\n"
        f"warmup {cfg.get('WARMUP_TRACES', '?')} (thin) -> frozen bar -> online wave (thick), "
        f"instant cut below the bar | tau = {cfg.get('CONSENSUS', '?')} | model: {cfg['MODEL']}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=4)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid:02d}_deepconf_confidence_timeline.png"   # zero-padded so they sort
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
