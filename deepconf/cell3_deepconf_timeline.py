# ========= CELL 3 (DeepConf) — BASELINE TIMELINES (run after baseline races) =========
# Draws the game tape of a DeepConf-low/high baseline run: every trace's
# sliding-window confidence, split into the two phases that define the method —
#   WARMUP  (the first 16 traces, run unjudged to completion; they calibrate
#            the bar and cast the anchor ballots)
#   ONLINE  (every later trace, judged INSTANTLY against the frozen bar)
# The frozen bar is the horizontal line; online traces that dipped below it die
# at the crossing (black X, usually moments after their first full window).
# Colors: green = finished correct, red = wrong majority, light red = other
# wrong, gray + X = cut at the frozen bar, khaki dashed = no answer.
# Warmup traces are drawn solid; online traces slightly thinner.
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt

OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")

QIDS = "all"     # "all" = every saved deepconf run, or a set like [6]

WARMUP_N = 16    # DeepConf's published warmup size (trace ids 0..15)

def qid_of(fname):
    m = re.match(r"q(\d+)_", fname)
    return int(m.group(1)) if m else None

runs = sorted((f for f in os.listdir(OUT_DIR)
               if f.endswith(".pkl") and "deepconf" in f),
              key=lambda f: (qid_of(f) is None, qid_of(f)))
print("saved deepconf runs:", runs)
if QIDS != "all":
    wanted = set(QIDS)
    runs = [f for f in runs if qid_of(f) in wanted]
if not runs:
    raise SystemExit("No saved deepconf runs match QIDS — run the baseline first.")

def draw_timeline(fname):
    with open(f"{OUT_DIR}/{fname}", "rb") as f:
        r = pickle.load(f)

    qid, gt = r["qid"], str(r["gt"])
    cfg     = r["config"]
    WINDOW  = cfg["WINDOW"]
    bar     = cfg.get("final_line")        # the frozen warmup bar

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

    warm_toks   = sum(t["toks_gen"] for t in r["traces"] if t["id"] < WARMUP_N)
    online_toks = sum(t["toks_gen"] for t in r["traces"] if t["id"] >= WARMUP_N)
    n_cut       = sum(1 for t in r["traces"] if t["status"] == "stopped")

    fig, ax = plt.subplots(figsize=(16, 9))
    seen_labels = set()
    def label_once(lab):
        if lab in seen_labels: return None
        seen_labels.add(lab); return lab

    for t in r["traces"]:
        confs = t["confs"]
        if not confs: continue
        x = np.arange(len(confs)) + WINDOW
        step = max(1, len(confs) // 2000)
        xs, ys = x[::step], np.asarray(confs)[::step]
        warm = t["id"] < WARMUP_N
        lw_scale = 1.0 if warm else 0.75   # online traces slightly thinner

        if t["status"] == "stopped":       # executed at the frozen bar
            ax.plot(xs, ys, color="gray", lw=1.0 * lw_scale, alpha=0.7,
                    label=label_once("cut at the frozen bar (online wave)"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=1.8 * lw_scale,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            ax.plot(x[-1], confs[-1], "o", color="forestgreen", ms=5)
        elif t["status"] == "finished" and wrong_majority and str(t["answer"]) == wrong_majority:
            ax.plot(xs, ys, color="crimson", lw=1.8 * lw_scale,
                    label=label_once(f"wrong majority = {wrong_majority} (n={n_wmaj})"))
            ax.plot(x[-1], confs[-1], "o", color="crimson", ms=5)
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="lightcoral", lw=1.2 * lw_scale, alpha=0.85,
                    label=label_once("other wrong answers"))
            ax.plot(x[-1], confs[-1], "o", color="lightcoral", ms=4)
        else:
            ax.plot(xs, ys, color="darkkhaki", lw=1.2 * lw_scale, ls="--", alpha=0.9,
                    label=label_once("no answer (truncated/abandoned)"))
            ax.plot(x[-1], confs[-1], "o", color="darkkhaki", ms=4)

    if bar is not None:
        ax.axhline(bar, color="tab:blue", ls="-", lw=1.8,
                   label=f"FROZEN bar: {bar:.2f} (keep top "
                         f"{cfg.get('CONFIDENCE_PERCENTILE', '?')}% of warmup minima)")
        ax.annotate(f"bar frozen after warmup: {bar:.2f}", xy=(1.0, bar),
                    xycoords=("axes fraction", "data"), xytext=(-8, 6),
                    textcoords="offset points", ha="right", color="tab:blue")

    ax.set_xlabel(f"tokens generated (each point = sliding-window average of the "
                  f"previous {WINDOW} tokens)")
    ax.set_ylabel("sliding-window confidence")
    ax.set_title(
        f"DeepConf baseline, AIME25 Q{qid}: {len(r['traces'])} traces "
        f"(ground truth {gt}) | model: {cfg['MODEL']}\n"
        f"warmup: {WARMUP_N} full traces = {warm_toks:,} tokens ({warm_toks * 100 // max(r['tokens'], 1)}% "
        f"of the {r['tokens']:,} total) | online wave: {online_toks:,} tokens, "
        f"{n_cut} executed at the bar | consensus tau = {cfg.get('CONSENSUS', '?')}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid}_deepconf_timeline.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
