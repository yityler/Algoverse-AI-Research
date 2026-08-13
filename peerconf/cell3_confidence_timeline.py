# ============ CELL 3 — CONFIDENCE TIMELINES (run any time after runs) ============
# Draws the game tape from saved runs: every trace's sliding-window confidence over
# its life, colored by outcome, with the self-calibrating bar's armed and final
# levels. One figure per question. Pick which questions with QIDS below.
# Green = finished correct, red = the wrong majority, light red = other wrong
# answers, gray + X = cut at the bar, khaki dashed = truncated with no answer,
# blue dotted = drained when the run closed. Stars = graduated by a commitment
# probe; triangles = loop-guard harvests; small black dots along a trace mark
# where each graduation probe fired.
import os, re, pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

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

    # a wave-1 path whose worst moment fell under the vote bar still finishes and
    # still has an answer — it just does not get to cast it. Filled marker = its
    # ballot counted; hollow = it finished and was not counted.
    VBAR = cfg.get("vote_bar")
    def counted(t):
        return not (VBAR is not None and t["id"] < cfg.get("SEATS", 0)
                    and t["confs"] and min(t["confs"]) < VBAR)

    def end_marker(t, x_end, y_end, color):
        """How the trace left the run: * graduated | ^ loop-harvested | o natural.
        Hollow = finished but below the vote bar, so its answer was not counted."""
        ok = counted(t)
        if not ok:
            seen_labels.add("__novote__")
        style = (dict(color=color, mec="black", mew=0.5) if ok
                 else dict(color="none", mfc="none", mec=color, mew=1.6))
        if t.get("graduated"):
            ax.plot(x_end, y_end, "*", ms=14, **style,
                    label=label_once("graduated (commitment probe)"))
        elif t.get("looped"):
            ax.plot(x_end, y_end, "^", ms=9, **style,
                    label=label_once("loop-guard harvest"))
        else:
            ax.plot(x_end, y_end, "o", ms=6, **style)

    for t in r["traces"]:
        confs = t["confs"]
        if not confs: continue
        x = np.arange(len(confs)) + WINDOW         # confs[0] = the first full window
        step = max(1, len(confs) // 2000)          # downsample for the figure
        xs, ys = x[::step], np.asarray(confs)[::step]

        # weight says WHICH GROUP the path is in; colour still says how it ended.
        # wave 1 = the SEATS opening paths, drawn light; a replacement takes a
        # freed seat later and is drawn heavy
        wave1  = t["id"] < cfg.get("SEATS", 0)
        lw, al = ((1.1, 0.55) if wave1 else (2.1, 0.9))
        # a dotted line reads lighter than a solid one at the same weight, so the
        # broken styles get a floor: thin enough not to blob at replacement
        # weight, thick enough that a drained wave-1 path is still visible
        lw_dot, lw_dash = max(lw * 0.7, 1.0), max(lw * 0.85, 1.1)
        al_broken = max(al, 0.8)
        seen_labels.add("__w1__" if wave1 else "__rep__")

        # the probe schedule: one small dot per probe along the trace
        for p in t.get("probes", []):
            at = p.get("at", 0)
            if WINDOW <= at < len(confs) + WINDOW:
                ax.plot(at, confs[at - WINDOW], ".", color="black", ms=2.5, alpha=0.45,
                        label=label_once("graduation probe fired"))

        if t["status"] == "stopped" and t.get("looped"):
            # the loop guard, not the bar: it ends a repeating trace whatever
            # its confidence, so these can land well above the line
            ax.plot(xs, ys, color="dimgray", lw=lw, alpha=al)
            seen_labels.add("__loop__")
            ax.plot(x[-1], confs[-1], "^", color="black", ms=10, mew=1.0,
                    mfc="none")
        elif t["status"] == "stopped":             # cut at the bar
            ax.plot(xs, ys, color="gray", lw=lw, alpha=al,
                    label=label_once("cut at the bar"))
            ax.plot(x[-1], confs[-1], "x", color="black", ms=10, mew=2.2)
        elif t["status"] == "finished" and is_right(t["answer"]):
            ax.plot(xs, ys, color="forestgreen", lw=lw, alpha=al,
                    label=label_once(f"correct = {gt} (n={n_right})"))
            end_marker(t, x[-1], confs[-1], "forestgreen")
        elif t["status"] == "finished":
            ax.plot(xs, ys, color="crimson", lw=lw, alpha=al,
                    label=label_once(f"wrong (n={n_wrong})"))
            end_marker(t, x[-1], confs[-1], "crimson")
        elif t["status"] == "abandoned":           # drained when the run closed
            ax.plot(xs, ys, color="royalblue", lw=lw_dot, ls=":", alpha=al_broken,
                    label=label_once("drained (run closed early)"))
            ax.plot(x[-1], confs[-1], "s", color="royalblue", ms=4)
        else:                                      # truncated — cap or EOS, no answer
            ax.plot(xs, ys, color="darkgoldenrod", lw=lw_dash, ls="--", alpha=al_broken,
                    label=label_once("no answer (truncated)"))
            ax.plot(x[-1], confs[-1], "o", color="darkgoldenrod", ms=4)

    # the self-calibrating bar: armed level and final level, with the drift band.
    # (new pkls: line_history = bar updates; old pkls: the live line — the
    # same two-level rendering reads correctly for both)
    lh = r.get("line_history", [])
    keep = cfg.get("BAR_KEEP_TOP")
    bar_lab = (f"bar (keep top {keep}% of finishers' minima)" if keep
               else f"line (keep top {cfg.get('LINE_TOP', 0):.0%})")
    # armed and final get their own colours: blue is the drained traces, and one
    # blue for both levels made the bar look like it never moved
    ARMED, FINAL = "darkorange", "darkviolet"
    if lh:
        first, last = lh[0]["line"], lh[-1]["line"]
        ax.axhline(first, color=ARMED, ls="--", lw=1.8, zorder=6,
                   label=f"{bar_lab}: armed")
        ax.axhline(last, color=FINAL, ls="--", lw=1.8, zorder=6,
                   label=f"same bar: final, after {len(lh)} updates")
        ax.axhspan(min(first, last), max(first, last), color="0.45", alpha=0.08)
        # the higher level is tagged above its line and the lower one below, and
        # the two are pushed further apart when the bar barely moved, or the two
        # tags land on top of each other and neither reads
        y_lo, y_hi = ax.get_ylim()
        pad = 14 if abs(first - last) < 0.05 * (y_hi - y_lo) else 5
        dy_first, dy_last = ((pad, -pad - 9) if first >= last else (-pad - 9, pad))
        ax.annotate(f"armed: {first:.2f}", xy=(1.0, first),
                    xycoords=("axes fraction", "data"), xytext=(-8, dy_first),
                    textcoords="offset points", ha="right", color=ARMED, zorder=8,
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
        ax.annotate(f"final ({len(lh)} updates): {last:.2f}", xy=(1.0, last),
                    xycoords=("axes fraction", "data"), xytext=(-8, dy_last),
                    textcoords="offset points", ha="right", color=FINAL, zorder=8,
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))

    # the vote bar, on the questions that reached it: once wave 1 has departed,
    # a wave-1 path below this line no longer votes. Absent where the run closed
    # before wave 1 was done, so nothing is drawn there.
    # present only on runs whose wave 1 actually ran itself out; a run that
    # closed early and drained wave 1 never has one
    vbar = cfg.get("vote_bar")
    if vbar is not None:
        ax.axhline(vbar, color="darkcyan", ls="-.", lw=2.6, zorder=7,
                   label=f"vote bar (wave 1 must clear it to vote, top {keep}%)")
        ax.annotate(f"vote bar: {vbar:.2f}", xy=(0.0, vbar),
                    xycoords=("axes fraction", "data"), xytext=(8, 6),
                    textcoords="offset points", ha="left", color="darkcyan",
                    fontweight="bold", zorder=8,
                    bbox=dict(fc="white", ec="darkcyan", lw=0.8, alpha=0.9, pad=1.6))

    # the generation cap, when the pkl recorded it: a khaki trace that ends here
    # was truncated by the budget, not by anything the run decided
    cap = cfg.get("MAX_TOK_TRACE")
    if cap and any(len(t["confs"]) + WINDOW >= cap * 0.98 for t in r["traces"] if t["confs"]):
        ax.axvline(cap, color="darkgoldenrod", ls=":", lw=1.2, alpha=0.8)
        ax.annotate(f"cap {cap:,}", xy=(cap, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(-4, -12), textcoords="offset points",
                    ha="right", color="darkgoldenrod", fontsize=9)

    probe_every = cfg.get("PROBE_EVERY")
    sub = (f"wave 1: {cfg.get('SEATS', 0)} opening paths (thin) -> replacements take "
           f"freed seats (thick), bar cuts instantly | "
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
    handles, labels = ax.get_legend_handles_labels()
    # the group key: neutral grey, because here it is the WEIGHT that means
    # something, not the colour
    if "__w1__" in seen_labels:
        handles.append(Line2D([], [], color="black", lw=1.1, alpha=0.55))
        labels.append(f"wave 1: the {cfg.get('SEATS', 0)} opening paths (thin)")
    if "__rep__" in seen_labels:
        handles.append(Line2D([], [], color="black", lw=2.1, alpha=0.9))
        labels.append("replacement: took a freed seat later (thick)")
    if "__novote__" in seen_labels:
        handles.append(Line2D([], [], ls="none", marker="o", ms=7,
                              mfc="none", mec="0.25", mew=1.6))
        labels.append("finished but under the vote bar: not counted")
    if "__loop__" in seen_labels:
        handles.append(Line2D([], [], color="dimgray", lw=1.2, marker="^",
                              ms=9, mfc="none", mec="black", mew=1.0))
        labels.append("ended by the loop guard")
    ax.legend(handles, labels, loc="upper center",
              bbox_to_anchor=(0.5, -0.09), ncol=4)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out_png = f"{OUT_DIR}/q{qid:02d}_peerconf_confidence_timeline.png"   # zero-padded so they sort
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    print(f"Saved {out_png}")
    plt.show()
    plt.close(fig)

for fname in runs:
    draw_timeline(fname)
