# ======================= CELL 2 — THE RACE (the streaming belt) =======================
# Loops over every question in QIDS: one full race per question, one pkl per question.
# A question whose pkl already exists in OUT_DIR is skipped, so an interrupted sweep
# resumes with a simple rerun (delete a pkl to redo that question from scratch).
import json, re, time, pickle, os, queue, threading
import numpy as np, requests
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from transformers import AutoTokenizer
from dynasor.core.evaluator import math_equal

# ==================== PeerConf CONTROL PANEL ====================

MODEL   = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
SERVER  = "http://localhost:8000"
OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")   # where results are saved

QIDS           = range(30)  # which AIME problems to run — all 30, or a set like [6, 9]
SEATS          = 16       # traces in flight at once — the belt's chairs
MAX_TRACES     = 32       # total launch cap. A departed trace frees its seat for a
                          # fresh one until this cap — or the landslide rule ends the
                          # race first (CONSENSUS below).

# ----- the line (drawn live from the field's worst moments) -----
LINE_TOP       = 0.95     # keep the top 95% of the field: the line sits where only
                          # the worst ~5% of per-trace WORST MOMENTS fall below it.
                          # Structural guarantee: the best trace's minimum is always
                          # >= the line; a zero-finisher wipeout is impossible by
                          # construction.
WINDOW         = 2048     # sliding window: a token's score = avg confidence of its
                          # last 2048 tokens. FULL windows only — partial-window
                          # means are startup noise.
STREAM_BATCH   = 1        # tokens are STREAMED. Every STREAM_BATCH tokens the worker
                          # reports in and the main thread runs pour -> redraw ->
                          # judge. At 1, judgment is TOKEN-EXACT: a cut lands at the
                          # crossing. (judge_min is O(1), line history records only
                          # changes, so 1 is cheap.)
DWELL_TOKENS   = 128      # sustained crossing required before a verdict — a graze
                          # below the line shorter than this is forgiven, so
                          # first-window noise is never fatal.
# Judgment starts the moment a trace has poured its first full window (token 2048):
# pour precedes judge. No extra grace period.

# ----- the response (what happens when a trace is judged below the line) -----
DIP_ACTION     = "stop"    # "stop"    = cut: stream closed, no relaunch
                           # "reflect" = reflection prompt; the trace continues and
                           #             can still vote
STOP_ON_RELAPSE = False    # (only used when DIP_ACTION="reflect")
                           # False = reflected traces run unjudged to the end and vote
                           # True  = reflected traces stay judged on their POST-
                           #         reflection scores; a second dip = cut

# ----- the final check (the blind-spot guard) -----
FINAL_CHECK    = "wait"   # fires ONCE per trace, the moment it boxes an answer,
                          # BEFORE that answer is accepted for the election:
                          #   "off"  = no second look — answer stands
                          #   "wait" = splice "Wait" into the trace's own text and let
                          #            it keep thinking
                          #            (Self-Correction Bench, arXiv:2507.02778)
FINAL_CHECK_TOKENS = 4000 # token cap for the verification leg (streamed like any
                          # leg, but never judged)
FORCE_BOXED    = False    # True = append "Please put your final answer within
                          # \boxed{}." to the prompt.

# ----- early stopping (the landslide rule) -----
CONSENSUS      = 0.95     # checked after EVERY finished trace; if the leading answer
                          # holds this share of the weighted votes among finished
                          # traces (and >=3 have finished), stop launching AND kill
                          # the in-flight streams on the spot — the belt drains
                          # instantly. 2.0 = DISABLED (share caps at 1.0).

# ----- generation -----
TEMPERATURE    = 0.6
TOP_P          = 0.95
TOP_K          = 20
LOGPROBS       = 20       # top-20 candidates per token — the confidence data
MAX_TOK_TRACE  = 30000    # total generation cap per trace, counted in tokens GENERATED
# ================================================================

tok    = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
EOS_ID = tok.eos_token_id

with open("aime25.jsonl") as f:
    data = [json.loads(l) for l in f]

def render_chat(user_text):
    return tok.apply_chat_template([{"role": "user", "content": user_text}],
                                   tokenize=False, add_generation_prompt=True)

FINAL_CHECK_TEXT = {
    "wait": "\nWait",
}

SESSION = requests.Session()

def build_reflect_prompt(path_text):
    """Fresh-prompt reflection, third-person framing."""
    body = (question + "\n\n"
            "Another model's reasoning process was interrupted because its "
            "confidence dropped significantly, indicating a likely flaw in its most "
            "recent steps. Its reasoning so far:\n" + path_text + "\n\n"
            "Task: Analyze the final part of its reasoning. Identify the error or "
            "uncertainty, and provide a corrected, rigorous continuation.")
    return render_chat(body)

def is_correct(ans, gt):
    if ans is None: return False
    try:    return math_equal(str(ans), gt)
    except: return str(ans) == gt

def extract_answer(text):
    hits = re.findall(r"\\boxed\{([^{}]*)\}", text)
    return hits[-1].strip() if hits else None

class Trace:
    def __init__(self, tid):
        self.id = tid
        self.prompt_text = BASE_PROMPT  # replaced by the fresh reflection prompt on reflection
        self.gen_text  = ""      # generated text for the CURRENT prompt
        self.confs     = []      # full-window score per token (whole life) — the
                                 # confidence timeline, saved for the figure
        self.win       = None    # window deque, carried across legs (worker-owned in flight)
        self.toks_gen  = 0       # every token the GPU generated, across all prompts
        self.judge_from = 0      # index into confs where judgment starts (moves on
                                 # reflection so relapse-judgment sees only new scores)
        self.judge_min = float("inf")  # running min of confs[judge_from:], kept
                                 # incrementally so judging is O(1) even at
                                 # STREAM_BATCH = 1 (game tape + cut printout)
        self.below_run = 0       # consecutive tokens the CURRENT score has spent
                                 # below the line — the dwell counter
        self.kill      = threading.Event()  # the kill switch: set by the main thread,
                                 # honored by the worker, which closes the stream
        self.pending   = None    # None | "cut" | "reflect" — verdict awaiting stream close
        self.reflected = False
        self.dipped    = False
        self.checked   = False   # has the blind-spot guard fired for this trace?
        self.checking  = False   # is it out on its verification leg right now?
        self.check_confs = []    # verification-leg scores — game tape only
        self.pre_check_answer = None
        self.revised   = False
        self.retried   = False
        self.status    = "racing"   # racing|finished|stopped|truncated|abandoned
        self.answer    = None

def current_line():
    """The line over LIVE per-trace minima; None until every opening seat has
    poured once."""
    if len(MINS) < SEATS: return None
    return float(np.percentile(list(MINS.values()), (1 - LINE_TOP) * 100))

def consensus_check():
    piles = {}
    for t in traces:
        if t.status == "finished" and t.answer is not None and t.confs:
            piles[t.answer] = piles.get(t.answer, 0.0) + min(t.confs)
    if not piles: return None, 0.0
    a = max(piles, key=piles.get)
    return a, piles[a] / sum(piles.values())

def fly_stream(t, prompt_text, max_toks):
    """Worker thread: ONE streaming leg. Tokens arrive live with their top-20
    logprobs; the worker keeps the window math locally, reports to the main thread
    every STREAM_BATCH tokens, and honors the kill switch by closing the stream
    (the server aborts generation on disconnect)."""
    body = {"model": MODEL, "prompt": prompt_text,
            "max_tokens": int(max_toks), "temperature": TEMPERATURE,
            "top_p": TOP_P, "top_k": TOP_K, "logprobs": LOGPROBS, "stream": True}
    try:
        r = SESSION.post(f"{SERVER}/v1/completions", json=body, stream=True, timeout=7200)
        r.raise_for_status()
        win = t.win if t.win is not None else deque(maxlen=WINDOW)
        s = sum(win)
        b_scores, b_text, b_toks = [], [], 0
        fin = None
        for raw in r.iter_lines():
            if t.kill.is_set():                      # the kill switch
                r.close()
                fin = fin or "killed"
                break
            if not raw: continue
            if not raw.startswith(b"data: "): continue
            payload = raw[6:]
            if payload == b"[DONE]": break
            ch = json.loads(payload)["choices"][0]
            b_text.append(ch.get("text") or "")
            lps = (ch.get("logprobs") or {}).get("top_logprobs") or []
            for d in lps:
                if not d: continue
                vals = sorted(d.values(), reverse=True)[:LOGPROBS]
                c = -float(np.mean(vals))                          # -sum(top-20)/20
                if len(win) == WINDOW: s -= win[0]
                win.append(c); s += c
                b_toks += 1
                if len(win) == WINDOW:            # full windows only
                    b_scores.append(s / len(win))
            if ch.get("finish_reason"):
                fin = ch["finish_reason"]
            if b_toks >= STREAM_BATCH:
                events.put((t, {"kind": "batch", "text": "".join(b_text),
                                "scores": b_scores, "ntok": b_toks}, None))
                b_scores, b_text, b_toks = [], [], 0
        t.win = win                                   # carried to the next leg
        events.put((t, {"kind": "end", "text": "".join(b_text),
                        "scores": b_scores, "ntok": b_toks,
                        "finish": fin or "stop"}, None))
    except Exception as e:
        events.put((t, None, e))

def launch(t):
    """Main thread only. One streaming leg: the whole remaining budget (race leg)
    or the verification cap (check leg). Judgment happens live, at every report."""
    if t.checking:
        budget = min(MAX_TOK_TRACE - t.toks_gen, FINAL_CHECK_TOKENS)
    else:
        budget = MAX_TOK_TRACE - t.toks_gen
    t.kill = threading.Event()
    t.pending = None
    inflight.add(t.id)
    executor.submit(fly_stream, t, t.prompt_text + t.gen_text, max(budget, 1))

def pour_and_judge(t, scores):
    """POUR the batch's low into the bucket, REDRAW the line, then JUDGE this trace.
    Returns the verdict: None (safe) | 'cut' | 'reflect'."""
    global line_live, last_line
    if scores:
        m = min(scores)
        if t.id not in MINS or m < MINS[t.id]:
            MINS[t.id] = m
        if m < t.judge_min:
            t.judge_min = m
    line = current_line()
    if line is None:
        return None
    if not line_live:
        line_live = True
        print(f"Line live at {line:.3f} ({len(MINS)} trace minima)")
    if line != last_line:
        last_line = line
        LINE_HISTORY.append({"tid": t.id, "line": line,
                             "n_traces": len(MINS), "t": time.time() - t_start})
    judged = (DIP_ACTION == "stop") or (not t.reflected) or STOP_ON_RELAPSE
    if not judged:
        return None
    for sc in scores:                 # the dwell: sustained crossing, not a graze
        if sc < line:
            t.below_run += 1
            if t.below_run >= DWELL_TOKENS:
                return "cut" if (DIP_ACTION == "stop" or
                                 (t.reflected and STOP_ON_RELAPSE)) else "reflect"
        else:
            t.below_run = 0
    return None

# ---------------- voting helpers (used once per question, after its race) ----------------
def trace_measures(t):
    c = np.array(t.confs) if t.confs else np.array([0.0])
    k = max(1, int(len(c) * 0.10))
    return {"mean_conf":     float(c.mean()),
            "tail_conf":     float(c[-1]),
            "bottom_window": float(np.sort(c)[:k].mean()),
            "min_window":    float(c.min())}

def weighted_vote(weight_key=None, only_traces=None):
    pool = only_traces if only_traces is not None else voters
    piles = {}
    for t in pool:
        w = 1.0 if weight_key is None else M[t.id][weight_key]
        piles[str(t.answer)] = piles.get(str(t.answer), 0.0) + float(w)
    if not piles: return None, None, 0
    a = max(piles.keys(), key=lambda x: piles[x])
    conf = float(np.mean([M[t.id][weight_key] for t in pool])) if weight_key else None
    return a, conf, len(pool)

def top_filtered(measure, top_percent=0.1):
    if not voters:
        return None, None, 0
    confs = [M[t.id][measure] for t in voters]
    thr   = np.percentile(confs, (1 - top_percent) * 100)
    elite = [t for t in voters if M[t.id][measure] >= thr]
    return weighted_vote(measure, only_traces=elite)

executor = ThreadPoolExecutor(max_workers=SEATS + 4)
os.makedirs(OUT_DIR, exist_ok=True)
t_sweep = time.time()

# ==================== THE SWEEP: one race per question ====================
for QID in QIDS:
    save_path = f"{OUT_DIR}/q{QID}_{DIP_ACTION}_{FINAL_CHECK}_belt.pkl"
    if os.path.exists(save_path):
        print(f"Q{QID}: already saved ({save_path}) — skipping")
        continue

    print(f"\n{'=' * 60}\n### Q{QID}  ({(time.time() - t_sweep) / 60:.0f} min into the sweep)\n{'=' * 60}")
    question, ground_truth = data[QID]["question"], str(data[QID]["answer"]).strip()
    if FORCE_BOXED:                    # question feeds the main prompt AND the reflection prompt
        question += "\n\nPlease put your final answer within \\boxed{}."
    print(f"Q{QID}: {question[:80]}...\nGround truth: {ground_truth}\n")
    BASE_PROMPT = render_chat(question)

    # -------- fresh race state (mutated ONLY by the main thread) --------
    traces    = [Trace(i) for i in range(SEATS)]
    launched  = SEATS
    MINS      = {}               # {trace id: its worst full-window score EVER} — one
                                 # entry per trace, never deleted (anchoring)
    LINE_HISTORY = []            # game tape: the line at every change, for the figure
    t_start   = time.time()
    events    = queue.Queue()    # (trace, payload|None, error|None) from worker threads
    inflight  = set()
    race_over = False
    n_events  = 0
    line_live = False
    last_line = None             # LINE_HISTORY records only line CHANGES, so the
                                 # game tape stays small even at STREAM_BATCH = 1

    # -------- the streaming belt: pour -> redraw -> judge, live --------
    print(f"Race start: {SEATS} seats, streaming (report every {STREAM_BATCH} tokens), "
          f"keep top {LINE_TOP:.0%} of the field (line = "
          f"{(1 - LINE_TOP) * 100:.0f}th pct of trace minima)")
    for t in traces:
        launch(t)

    while inflight:
        t, payload, err = events.get()
        n_events += 1

        if err:                                               # one retry, then truncate
            inflight.discard(t.id)
            if not t.retried:
                t.retried = True
                print(f"Trace {t.id}: stream error, retrying ({err})")
                launch(t); continue
            t.status = "truncated"
            print(f"Trace {t.id}: stream failed twice -> truncated ({err})")
        elif payload["kind"] == "batch":                      # mid-flight report
            t.gen_text += payload["text"]; t.toks_gen += payload["ntok"]
            if t.checking:
                t.check_confs += payload["scores"]
            else:
                t.confs += payload["scores"]
                if t.pending is None and not race_over:
                    verdict = pour_and_judge(t, payload["scores"])
                    if verdict is not None:
                        t.dipped = True
                        t.pending = verdict
                        t.kill.set()                          # stream closes within a chunk
            continue                                          # trace still in flight
        else:                                                 # "end": the leg is over
            inflight.discard(t.id)
            t.gen_text += payload["text"]; t.toks_gen += payload["ntok"]
            fin = payload["finish"]
            if t.checking:
                t.check_confs += payload["scores"]
            else:
                t.confs += payload["scores"]
                if t.pending is None and not race_over and payload["scores"]:
                    verdict = pour_and_judge(t, payload["scores"])
                    if verdict is not None:
                        t.dipped = True
                        t.pending = verdict

            ans = extract_answer(t.gen_text) if fin == "stop" else None
            line = current_line()

            if race_over:                                     # landed after the landslide
                if t.checking and t.pre_check_answer is not None:
                    t.status, t.answer, t.checking = "finished", t.pre_check_answer, False
                else:
                    t.status = "abandoned"
            elif t.pending == "reflect":                      # rescue — INSTANTLY
                t.prompt_text = build_reflect_prompt(t.gen_text)
                t.gen_text    = ""
                t.win         = None
                t.reflected   = True
                t.judge_from  = len(t.confs)                  # relapse looks only forward
                t.judge_min   = float("inf")
                t.below_run   = 0
                print(f"Trace {t.id}: reflection fired at {t.toks_gen} tokens")
                launch(t); continue
            elif t.pending == "cut":                          # the kill switch landed
                t.status = "stopped"
                print(f"Trace {t.id}: cut at the line "
                      + (f"{line:.3f} " if line is not None else "")
                      + f"(its low {t.judge_min:.3f}, {t.toks_gen} tokens)")
            elif t.checking:                                  # back from its verification leg
                t.checking = False
                t.status   = "finished"
                ans2 = extract_answer(t.gen_text)             # LAST box wins, else the
                t.answer  = ans2 if ans2 is not None else t.pre_check_answer
                t.revised = (str(t.answer) != str(t.pre_check_answer))
                print(f"Trace {t.id}: {FINAL_CHECK} check done at {t.toks_gen} tokens | "
                      f"answer={t.answer}"
                      + (f" (REVISED from {t.pre_check_answer})" if t.revised else " (confirmed)"))
            elif ans is not None:                             # crossed the finish line
                if FINAL_CHECK != "off" and not t.checked and t.toks_gen < MAX_TOK_TRACE:
                    t.checked, t.checking = True, True
                    t.pre_check_answer = ans
                    t.gen_text += FINAL_CHECK_TEXT[FINAL_CHECK]
                    print(f"Trace {t.id}: boxed {ans} at {t.toks_gen} tokens -> "
                          f"{FINAL_CHECK} check fired")
                    launch(t); continue                       # verification leg, instantly
                t.status, t.answer = "finished", ans
                print(f"Trace {t.id}: finished at {t.toks_gen} tokens | answer={ans}"
                      + (" | was reflected" if t.reflected else ""))
            elif fin == "stop":                               # EOS without a boxed answer
                t.status = "truncated"
                print(f"Trace {t.id}: ended without a boxed answer at {t.toks_gen} "
                      f"tokens -> truncated")
            else:                                             # hit its budget
                t.status = "truncated"
                print(f"Trace {t.id}: truncated at {t.toks_gen} tokens (cap)")

        # ---- this trace departed: per-trace pit stop ----
        if CONSENSUS <= 1.0 and not race_over:
            lead, share = consensus_check()
            n_fin = sum(1 for x in traces if x.status == "finished")
            if lead is not None and share >= CONSENSUS and n_fin >= 3:
                race_over = True
                live_ids = [x.id for x in traces if x.id in inflight]
                for x in traces:                              # drain INSTANTLY
                    if x.id in inflight:
                        x.kill.set()
                print(f"Consensus after {n_fin} finishers: '{lead}' holds {share:.0%} — "
                      f"killing {len(live_ids)} in-flight streams, no new launches")
        if not race_over and launched < MAX_TRACES:
            nt = Trace(launched); traces.append(nt)
            nl = current_line()
            print(f"Trace {launched}: seated (replacing {t.id})"
                  + (f" | line now {nl:.3f}" if nl is not None else ""))
            launched += 1
            launch(nt)

    # -------- results + voting table --------
    done   = traces
    voters = [t for t in done if t.status == "finished" and t.answer is not None]
    M = {t.id: trace_measures(t) for t in voters}

    print(f"\nBasic voting candidates: {len(voters)}")
    print(f"Sample voting answers: {[t.answer for t in voters][:8]}")
    voting_results = {
        "majority":                     weighted_vote(None),
        "mean_confidence_weighted":     weighted_vote("mean_conf"),
        "tail_confidence_weighted":     weighted_vote("tail_conf"),
        "bottom_window_weighted":       weighted_vote("bottom_window"),
        "min_window_weighted":          weighted_vote("min_window"),
        "top10_tail_filtered":          top_filtered("tail_conf", 0.10),
        "top10_bottom_window_filtered": top_filtered("bottom_window", 0.10),
    }

    total_tokens = sum(t.toks_gen for t in done)
    n_status     = lambda s: sum(1 for x in done if x.status == s)
    n_reflected  = sum(1 for t in done if t.reflected)
    salvaged     = sum(1 for t in done if t.reflected and t.status == "finished"
                       and t.answer is not None and is_correct(t.answer, ground_truth))
    n_checked    = sum(1 for t in done if t.checked)
    n_revised    = sum(1 for t in done if t.revised)
    # blind-spot guard scoring: only traces whose PRE-check answer was wrong were in
    # danger — confirming an already-correct answer is excluded from the rate entirely
    guard_done    = [t for t in done if t.checked and t.status == "finished"]
    guard_at_risk = [t for t in guard_done if not is_correct(t.pre_check_answer, ground_truth)]
    guard_rescued = sum(1 for t in guard_at_risk if is_correct(t.answer, ground_truth))
    guard_wrecked = sum(1 for t in guard_done
                        if is_correct(t.pre_check_answer, ground_truth)
                        and not is_correct(t.answer, ground_truth))
    # overall save rate: every trace that was ever in danger (dipped -> reflected, or
    # boxed a wrong answer) and still ended finished + correct — no double counting
    in_danger = [t for t in done if t.reflected
                 or (t.checked and t.status == "finished"
                     and not is_correct(t.pre_check_answer, ground_truth))]
    saved     = sum(1 for t in in_danger if t.status == "finished"
                    and is_correct(t.answer, ground_truth))

    final_line = current_line()
    print("\n=== PeerConf Summary (streaming belt) ===")
    print(f"Dip action: {DIP_ACTION} | stop on relapse: {STOP_ON_RELAPSE} | final check: {FINAL_CHECK}")
    print(f"Final line: {final_line if final_line is None else f'{final_line:.3f}'} "
          f"(keep top {LINE_TOP:.0%} of {len(MINS)} trace minima) | "
          f"seats {SEATS} | launched {launched}/{MAX_TRACES} | events: {n_events}")
    print(f"Traces: finished {n_status('finished')} | stopped {n_status('stopped')} "
          f"| truncated {n_status('truncated')} | abandoned {n_status('abandoned')}")
    print(f"Dipped: {sum(1 for t in done if t.dipped)} | reflections fired: {n_reflected} "
          f"| salvage rate (correct): {salvaged}/{n_reflected}" if n_reflected else
          f"Dipped: {sum(1 for t in done if t.dipped)} | reflections fired: 0 | salvage rate: 0/0")
    if FINAL_CHECK != "off":
        print(f"Blind-spot guard ({FINAL_CHECK}): fired on {n_checked} | revised: {n_revised} | "
              f"rescued {guard_rescued}/{len(guard_at_risk)} wrong answers | broke {guard_wrecked} correct ones")
    print(f"Overall save rate: {saved}/{len(in_danger)} in-danger traces ended correct")
    print(f"Valid answers for voting: {len(voters)}")
    print(f"Final answer: {voting_results['majority'][0]}   | ground truth: {ground_truth}")
    print(f"Total tokens generated (all traces, incl. discarded): {total_tokens}")
    print(f"Total time: {time.time()-t_start:.2f}s")

    print("\n=== Voting Results Summary ===")
    for m, (a, conf, v) in voting_results.items():
        cs = f" (conf: {conf:.3f})" if conf is not None else ""
        print(f"  {m}: {a}{cs} [{v} votes]")

    print("\n=== Detailed Voting Results ===")
    print("-" * 70)
    print(f"{'Method':<30}{'Answer':<12}{'Votes':<7}{'Confidence':<12}{'Correct'}")
    print("-" * 70)
    for m, (a, conf, v) in voting_results.items():
        ok = "✓" if is_correct(a, ground_truth) else "✗"
        cs = f"{conf:.3f}" if conf is not None else "-"
        print(f"{m:<30}{str(a):<12}{v:<7}{cs:<12}{ok}")
    marks = ", ".join(f"{m}:{'✓' if is_correct(r[0], ground_truth) else '✗'}" for m, r in voting_results.items())
    print(f"Q{QID} done | gt={ground_truth} | {marks}")

    # -------- save (results + the confidence-timeline game tape) --------
    with open(save_path, "wb") as f:
        pickle.dump({"qid": QID, "gt": ground_truth,
                     "config": {"MODE": "server-stream-belt", "MODEL": MODEL,
                                "LINE_TOP": LINE_TOP,
                                "WINDOW": WINDOW, "STREAM_BATCH": STREAM_BATCH,
                                "DWELL_TOKENS": DWELL_TOKENS,
                                "DIP_ACTION": DIP_ACTION,
                                "STOP_ON_RELAPSE": STOP_ON_RELAPSE,
                                "FINAL_CHECK": FINAL_CHECK,
                                "FINAL_CHECK_TOKENS": FINAL_CHECK_TOKENS,
                                "FORCE_BOXED": FORCE_BOXED,
                                "SEATS": SEATS, "MAX_TRACES": MAX_TRACES,
                                "CONSENSUS": CONSENSUS, "final_line": final_line},
                     "voting": voting_results, "tokens": total_tokens, "launched": launched,
                     "line_history": LINE_HISTORY,
                     "mins": MINS,
                     "salvage": (salvaged, n_reflected),
                     "guard":   (guard_rescued, len(guard_at_risk), guard_wrecked),
                     "saved":   (saved, len(in_danger)),
                     "traces": [{"id": t.id, "status": t.status, "answer": t.answer,
                                 "reflected": t.reflected, "dipped": t.dipped,
                                 "checked": t.checked, "revised": t.revised,
                                 "pre_check_answer": t.pre_check_answer,
                                 "toks_gen": t.toks_gen,
                                 "confs": t.confs,
                                 "check_confs": t.check_confs,
                                 "text": t.gen_text,
                                 "prompt": t.prompt_text} for t in done]}, f)
    print(f"Saved to {save_path}")

print(f"\nSweep over: {len(list(QIDS))} questions requested, "
      f"{(time.time() - t_sweep) / 60:.0f} min total")
