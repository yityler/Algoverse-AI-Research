# ============ CELL 3 — CONFIDENCE TIMELINES (run any time after CELL 2) ============
# Draws the game tape from saved runs: every trace's sliding-window confidence
# over its life, colored by outcome, with the frozen warmup bar. One figure per
# question. Pick which questions with QIDS below.
# Green = the trace's own answer is correct, crimson = it is wrong, both judged
# with cell2's own grader so the figure can never disagree with the results table.
# Which wrong answer happened to lead is deliberately not distinguished: one colour
# for every wrong answer, because two reds for "wrong" and "also wrong" only made
# the figure harder to read. Green never depends on the vote either, so a path that
# answered correctly and was outvoted is still green.
# gray + X = cut at the bar, khaki dashed = truncated with no answer,
# steel dotted = drained when consensus closed the run. Thin lines = warmup
# traces (never judged), thick lines = the online wave.
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from dynasor.core.evaluator import math_equal

# ---- grading, kept identical to cell2's -------------------------------------
# A figure that colours a trace green while the run counted it wrong is worse than
# no figure. cell2 grades with tidy_tex + math_equal, so this does too, rather
# than with the exact string match that used to live in is_right() below.
#
# These two functions are a VERBATIM copy of cell2's. cell2 is a script that runs
# a whole sweep on import, so it cannot be imported from; the copy is the only way
# to share the logic. If cell2's grading changes, change it here too -- the figure
# silently disagreeing with the results table is exactly the failure this is meant
# to prevent.
_WS_G = re.compile(r"\s+")


def tidy_tex(a):
    """Cosmetic LaTeX only. Same value, fewer ways to write it."""
    s = str(a)
    for x, y in ((r"\dfrac", r"\frac"), (r"\tfrac", r"\frac"),
                 (r"\left", ""), (r"\right", ""),
                 (r"\!", ""), (r"\,", " "), (r"\;", " "), (r"\ ", " ")):
        s = s.replace(x, y)
    return _WS_G.sub(" ", s).strip()


def same_answer(a, b):
    """Do these two strings name the same value? Cheap tests first, then
    math_equal, which is what catches 0.5 against \\frac{1}{2}."""
    if a is None or b is None:
        return False
    a, b = tidy_tex(a), tidy_tex(b)
    if a == b or _WS_G.sub("", a) == _WS_G.sub("", b):
        return True
    try:
        return bool(math_equal(a, b))
    except Exception:
        return False

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
        # the run's own grader, not a string compare: a trace that wrote
        # \dfrac{14}{3} against a gold of \frac{14}{3} was counted correct by
        # cell2 and must be drawn correct here
        return same_answer(ans, gt)

    # one colour for every wrong answer: which wrong answer led is not the point,
    # and two reds for "wrong" and "also wrong" only made the figure harder to read
    finished = [t for t in r["traces"] if t["status"] == "finished" and t["answer"] is not None]
    n_right  = sum(1 for t in finished if is_right(t["answer"]))
    n_wrong  = len(finished) - n_right

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
        # weight says WHICH PHASE the trace is in; colour still says how it
        # ended. warmup runs uncut, the online wave is judged at the frozen bar
        warm   = t.get("phase") == "warmup"
        lw, al = ((1.1, 0.55) if warm else (2.1, 0.9))
        # a dotted line reads lighter than a solid one at the same weight, so the
        # broken styles get a floor: thin enough not to blob at replacement
        # weight, thick enough that a drained wave-1 path is still visible
        lw_dot, lw_dash = max(lw * 0.7, 1.0), max(lw * 0.85, 1.1)
        al_broken = max(al, 0.8)
        seen_labels.add("__warm__" if warm else "__online__")

        if t["status"] == "stopped":               # cut at the bar
            ax.plot(xs, ys, color="gray", lw=lw, alpha=al,
                    label=label_once("cut at the bar"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=lw, alpha=al,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            ax.plot(x[-1], confs[-1], "o", color="forestgreen", ms=5)
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="crimson", lw=lw, alpha=al,
                    label=label_once(f"wrong (n={n_wrong})"))
            ax.plot(x[-1], confs[-1], "o", color="crimson", ms=5)
        elif t["status"] == "abandoned":           # drained when consensus closed the run
            ax.plot(xs, ys, color="steelblue", lw=lw_dot, ls=":", alpha=al_broken,
                    label=label_once("drained (consensus stop)"))
            ax.plot(x[-1], confs[-1], "s", color="steelblue", ms=4)
        else:                                      # truncated — cap or EOS, no answer
            ax.plot(xs, ys, color="darkkhaki", lw=lw_dash, ls="--", alpha=al_broken,
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
    # the group key: neutral grey, because here it is the WEIGHT that means
    # something, not the colour
    handles, labels = ax.get_legend_handles_labels()
    if "__warm__" in seen_labels:
        handles.append(Line2D([], [], color="black", lw=1.1, alpha=0.55))
        labels.append(f"warmup: the {cfg.get('WARMUP_TRACES', '?')} opening traces, "
                      f"never cut (thin)")
    if "__online__" in seen_labels:
        handles.append(Line2D([], [], color="black", lw=2.1, alpha=0.9))
        labels.append("online wave: judged at the bar (thick)")
    else:
        handles.append(Line2D([], [], ls="none"))
        labels.append("online wave never launched on this question")
    ax.legend(handles, labels, loc="upper center",
              bbox_to_anchor=(0.5, -0.09), ncol=4)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid:02d}_deepconf_confidence_timeline.png"   # zero-padded so they sort
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
