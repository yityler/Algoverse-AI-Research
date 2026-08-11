# ============ CELL 3 — CONFIDENCE TIMELINES (run any time after runs) ============
# Draws the game tape from saved runs: every trace's sliding-window confidence over
# its life, colored by outcome, with the self-calibrating bar's armed and final
# levels. One figure per question. Pick which questions with QIDS below.
# Green = finished correct, red = the wrong majority, light red = other wrong
# answers, gray + X = cut at the bar, khaki dashed = truncated with no answer,
# steel dotted = drained when the run closed. Stars = graduated by a commitment
# probe; triangles = loop-guard harvests; small dots along a trace = its probes.
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt

OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")

QIDS = "all"     # which questions to draw: "all" = every saved run,
                 # or a specific set like [6] or [6, 9, 12]

DATASET = os.environ.get("DATASET", "aime25")   # draw one benchmark at a time: the
                                                # same question number is a different
                                                # question in each benchmark

def qid_of(fname):                           # non-aime25 runs are <dataset>_q<N>_...
    m = re.match(r"(?:\w+?_)?q(\d+)_", fname)
    return int(m.group(1)) if m else None

def ds_of(fname):
    m = re.match(r"(?:(\w+?)_)?q\d+_", fname)
    return (m.group(1) or "aime25") if m else None

runs = sorted((f for f in os.listdir(OUT_DIR)
               if f.endswith(".pkl") and ds_of(f) == DATASET), key=qid_of)
print(f"saved {DATASET} runs:", runs)
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

    def end_marker(t, x_end, y_end, color):
        """How the trace left the run: * graduated | ^ loop-harvested | o natural."""
        if t.get("graduated"):
            ax.plot(x_end, y_end, "*", color=color, ms=14, mec="black", mew=0.5,
                    label=label_once("graduated (commitment probe)"))
        elif t.get("looped"):
            ax.plot(x_end, y_end, "^", color=color, ms=9, mec="black", mew=0.5,
                    label=label_once("loop-guard harvest"))
        else:
            ax.plot(x_end, y_end, "o", color=color, ms=5)

    for t in r["traces"]:
        confs = t["confs"]
        if not confs: continue
        x = np.arange(len(confs)) + WINDOW         # confs[0] = the first full window
        step = max(1, len(confs) // 2000)          # downsample for the figure
        xs, ys = x[::step], np.asarray(confs)[::step]

        # the probe schedule: one small dot per probe along the trace
        for p in t.get("probes", []):
            at = p.get("at", 0)
            if WINDOW <= at < len(confs) + WINDOW:
                ax.plot(at, confs[at - WINDOW], ".", color="black", ms=2.5, alpha=0.45)

        if t["status"] == "stopped":               # cut at the bar
            ax.plot(xs, ys, color="gray", lw=1.0, alpha=0.7,
                    label=label_once("cut at the bar"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=1.8,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            end_marker(t, x[-1], confs[-1], "forestgreen")
        elif t["status"] == "finished" and wrong_majority and str(t["answer"]) == wrong_majority:
            ax.plot(xs, ys, color="crimson", lw=1.8,
                    label=label_once(f"wrong majority = {wrong_majority} (n={n_wmaj})"))
            end_marker(t, x[-1], confs[-1], "crimson")
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="lightcoral", lw=1.2, alpha=0.85,
                    label=label_once("other wrong answers"))
            end_marker(t, x[-1], confs[-1], "lightcoral")
        elif t["status"] == "abandoned":           # drained when the run closed
            ax.plot(xs, ys, color="steelblue", lw=1.1, ls=":", alpha=0.8,
                    label=label_once("drained (run closed early)"))
            ax.plot(x[-1], confs[-1], "s", color="steelblue", ms=4)
        else:                                      # truncated — cap or EOS, no answer
            ax.plot(xs, ys, color="darkkhaki", lw=1.2, ls="--", alpha=0.9,
                    label=label_once("no answer (truncated)"))
            ax.plot(x[-1], confs[-1], "o", color="darkkhaki", ms=4)

    # the self-calibrating bar: armed level and final level, with the drift band.
    # (new pkls: line_history = bar updates; old pkls: the live line — the
    # same two-level rendering reads correctly for both)
    lh = r.get("line_history", [])
    keep = cfg.get("BAR_KEEP_TOP")
    bar_lab = (f"bar (keep top {keep}% of finishers' minima)" if keep
               else f"line (keep top {cfg.get('LINE_TOP', 0):.0%})")
    if lh:
        first, last = lh[0]["line"], lh[-1]["line"]
        ax.axhline(first, color="tab:blue", ls="--", lw=1.3, label=bar_lab)
        ax.axhline(last, color="tab:blue", ls="--", lw=1.3)
        ax.axhspan(min(first, last), max(first, last), color="tab:blue", alpha=0.06)
        ax.annotate(f"armed: {first:.2f}", xy=(1.0, first),
                    xycoords=("axes fraction", "data"), xytext=(-8, 6),
                    textcoords="offset points", ha="right", color="tab:blue")
        ax.annotate(f"final ({len(lh)} updates): {last:.2f}", xy=(1.0, last),
                    xycoords=("axes fraction", "data"), xytext=(-8, -14),
                    textcoords="offset points", ha="right", color="tab:blue")

    # the generation cap, when the pkl recorded it: a khaki trace that ends here
    # was truncated by the budget, not by anything the run decided
    cap = cfg.get("MAX_TOK_TRACE")
    if cap and any(len(t["confs"]) + WINDOW >= cap * 0.98 for t in r["traces"] if t["confs"]):
        ax.axvline(cap, color="darkkhaki", ls=":", lw=1.2, alpha=0.8)
        ax.annotate(f"cap {cap:,}", xy=(cap, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(-4, -12), textcoords="offset points",
                    ha="right", color="darkkhaki", fontsize=9)

    probe_every = cfg.get("PROBE_EVERY")
    sub = (f"bar cuts replacements instantly; wave 1 runs bar-free | "
           f"probes every {probe_every} tokens, graduate at {cfg.get('GRAD_CONF')} | "
           f"close: landslide {cfg.get('CONSENSUS', 0):.0%} or certificate"
           if probe_every else
           f"cut = {cfg.get('DWELL_TOKENS', '?')} consecutive tokens below the line")
    ax.set_xlabel(f"tokens generated (each point = sliding-window average: "
                  f"the confidence of the previous {WINDOW} tokens)")
    ax.set_ylabel("sliding-window confidence")
    ax.set_title(
        f"PeerConf, {cfg.get('DATASET', DATASET).upper()} Q{qid}: "
        f"sliding-window confidence of all {len(r['traces'])} traces "
        f"(window = {WINDOW} tokens, ground truth {gt})\n"
        f"{sub} | model: {cfg['MODEL']}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=4)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid}_confidence_timeline.png"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
