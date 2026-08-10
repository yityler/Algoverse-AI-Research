# ======================= CELL 2 — THE LIVE RUN (streaming) =======================
# Loops over every question in QIDS: one full run per question, one pkl per question.
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
DATASET = os.environ.get("DATASET", "aime25")         # aime25 | math500 | gsm8k | hmmt25
                                                      # = benchmarks/<name>.jsonl; any file
                                                      # of {"question","answer"} lines works

QIDS           = range(30)  # which questions to run — the first 30, or a set like [6, 9]
SEATS          = 16         # traces in flight at once
MAX_TRACES     = 32         # total launch cap: a departed trace frees its seat for a
                            # fresh one. Wave 1 is never judged; new paths face the
                            # armed bar from their first full window (token 2048)

# ----- the bar (PeerConf-low/high, from DeepConf-low/high) -----
# Self-calibrating: the run's own finishers are the warmup. Wave 1 (the first
# SEATS traces) runs bar-free; each finisher votes and sends its lifetime-worst
# window score to the calibration set (finishers ONLY — a cut path's minimum
# never joins it). The bar = keep top BAR_KEEP_TOP% of those minima, updated on
# every new finisher and applied instantly to every new path
BAR_KEEP_TOP        = 10  # 10 = PeerConf-low, 90 = PeerConf-high 
BAR_MIN_CALIBRATORS = 1   # the first finisher arms the bar (its worst moment IS
                          # the bar); every later finisher refines it

WINDOW         = 2048     # sliding window: a token's score = avg confidence of its
                          # last 2048 tokens. FULL windows only — partial-window
                          # means are startup noise.
STREAM_BATCH   = 1        # tokens are STREAMED: every STREAM_BATCH tokens the worker
                          # reports in and the main thread judges. At 1 a cut lands exactly at the crossing.
                          # A path is judged from its first full window (token 2048). The bar itself only
                          # moves when a finisher ends and sends its minimum.

# ----- the loop guard (text repetition; confidence is blind to loops) -----
LOOP_ACTION      = "cut"      # "off" | "cut" = end the stuck trace on the spot
                              # (a looping trace casts NO ballot: its text is
                              # pathology, not evidence)
LOOP_CHECK_EVERY = 256        # tokens between checks
LOOP_UNIT_CHARS  = 120        # repeat unit: the trace's last this-many chars
LOOP_TAIL_CHARS  = 2400       # ...searched within this much trailing text
LOOP_REPEATS     = 3          # fire at this many exact copies in the tail

# ----- the graduation probe (CoDE-Stop-style forced answer, fixed schedule) -----
PROBE_EVERY      = 4096       # probe each trace every this-many tokens. 0 = off
PROBE_TEXT       = "\n**Final Answer**\n\nThe final answer is \\boxed"
PROBE_MAX_TOK    = 20         # greedy tokens per probe
PROBE_MIN_TOKS   = 2048       # no probes before the first full window
GRAD_CONF        = 0.95       # graduate on ONE probe: answer-token conf >= this...
GRAD_EWT         = True       # ...that also reached </think> or <|end|> (ready to conclude and still need to add "<|end|>")

FORCE_BOXED    = False    # True = append "Please put your final answer within
                          # \boxed{}." to the prompt.

# ----- the certificate (second close): if (leader − runner-up) > (live +
# unlaunched), no possible future changes the winner: even if every path still
# out there voted runner-up, the leader still wins — so unlike the landslide's (MARS at gamma=1).

# ----- early stopping (the landslide rule) -----
CONSENSUS      = 0.95     # checked after EVERY finished trace; if the leading answer
                          # holds this share of the weighted votes among finished
                          # traces (and >=3 have finished), stop launching AND end
                          # the in-flight streams on the spot.
                          # Anything > 1.0 = DISABLED (a fraction of the votes can never beat 1.0;
                          # exactly 1.0 = stop only on unanimity).

# ----- generation -----
TEMPERATURE    = 0.6
TOP_P          = 0.95
TOP_K          = 0
LOGPROBS       = 20       # top-20 candidates per token — the confidence data
MAX_TOK_TRACE  = 64000    # total generation cap per trace, counted in tokens GENERATED
# ================================================================

tok    = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)

_bench = f"{DATASET}.jsonl"
_bench_paths = [_bench, os.path.join("benchmarks", _bench),
                os.path.join("..", "benchmarks", _bench)]
try:                                       # repo-root benchmarks/, found from the
    _here = os.path.dirname(os.path.abspath(__file__))   # script rather than the cwd
    _bench_paths[:0] = [os.path.join(_here, *([".."] * up), "benchmarks", _bench)
                        for up in (1, 2)]
except NameError:
    pass                                   # exec'd without __file__ (Modal)
_bench_path = next((p for p in _bench_paths if os.path.exists(p)), None)
if _bench_path is None:
    raise FileNotFoundError(f"{_bench} not found — looked in {_bench_paths}")
with open(_bench_path, encoding="utf-8") as f:
    data = [json.loads(l) for l in f]

# ask for a question the benchmark doesn't have and nothing runs: a sweep that
# quietly shortened itself would read as a full one in the results
QIDS = list(QIDS)
_bad = [q for q in QIDS if not 0 <= q < len(data)]
if _bad:
    raise SystemExit(f"{DATASET} has {len(data)} questions (0-{len(data) - 1}); "
                     f"QIDS asks for {_bad}")

DS_TAG = f"{DATASET}_"   # every result says which benchmark it came from, so two
                         # benchmarks can share an output dir without colliding
print(f"Benchmark: {DATASET} — {len(data)} questions from {_bench_path}, "
      f"running {len(QIDS)}")

def render_chat(user_text):
    return tok.apply_chat_template([{"role": "user", "content": user_text}],
                                   tokenize=False, add_generation_prompt=True)

SESSION = requests.Session()

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
        self.prompt_text = BASE_PROMPT
        self.gen_text  = ""      # generated text for the CURRENT prompt
        self.confs     = []      # full-window score per token (whole life) — the
                                 # confidence timeline, saved for the figure
        self.win       = None    # window deque, carried across legs (worker-owned in flight)
        self.toks_gen  = 0       # every token the GPU generated, across all prompts
        self.judge_min = float("inf")  # lifetime low of the window score — a
                                 # finisher sends this to the bar's calibration
        self.kill      = threading.Event()  # the kill switch: set by the main thread,
                                 # honored by the worker, which closes the stream
        self.pending   = None    # None | "cut" | "graduate"
                                 # — verdict awaiting stream close
        self.retried   = False
        self.probes    = []      # graduation-probe history: one dict per probe
        self.probe_toks = 0      # tokens the probes themselves generated (accounted)
        self.probing   = False   # a probe is in flight for this trace right now
        self.last_probe_at = 0   # toks_gen at the last probe (schedule pacing)
        self.last_loop_check = 0 # toks_gen at the last loop-guard check
        self.grad_answer = None  # the answer a successful probe read out
        self.looped    = False   # loop guard fired
        self.graduated = False   # finished early via the graduation probe
        self.status    = "running"   # running|finished|stopped|truncated|abandoned
        self.answer    = None

def update_bar():
    """Recompute the bar from the finishers' lifetime minima — the run's own
    finishers are the warmup, and the calibration sharpens with every new
    vote. Called after every finish."""
    global bar
    mins = [x.judge_min for x in traces
            if x.status == "finished" and x.confs]
    if len(mins) < BAR_MIN_CALIBRATORS:
        return
    new = float(np.percentile(mins, 100 - BAR_KEEP_TOP))
    if bar is None:
        print(f"Bar ARMED at {new:.3f} ({len(mins)} finishers calibrating, "
              f"keep top {BAR_KEEP_TOP}%)")
    bar = new
    LINE_HISTORY.append({"tid": -1, "line": bar, "n_traces": len(mins),
                         "t": time.time() - t_start})

def consensus_check():
    piles = {}
    for t in traces:
        if t.status == "finished" and t.answer is not None and t.confs:
            piles[t.answer] = piles.get(t.answer, 0.0) + min(t.confs)
    if not piles: return None, 0.0
    a = max(piles, key=piles.get)
    return a, piles[a] / sum(piles.values())

def certificate():
    """Election-calling: the run is over when the leader's ballot margin
    exceeds every vote that could still arrive. Exact counting — a wrong
    early call is arithmetically impossible."""
    piles = {}
    for x in traces:
        if x.status == "finished" and x.answer is not None:
            piles[x.answer] = piles.get(x.answer, 0) + 1
    if not piles:
        return None
    ranked = sorted(piles.values(), reverse=True)
    margin = ranked[0] - (ranked[1] if len(ranked) > 1 else 0)
    outstanding = len(inflight) + (MAX_TRACES - launched)
    if margin > outstanding:
        return max(piles, key=piles.get)
    return None

def looping(text):
    """Is the trace's tail an exact repeat? (Loops repeat verbatim at HIGH
    confidence, so text is the only guard that sees them.)"""
    unit = text[-LOOP_UNIT_CHARS:]
    if len(unit) < LOOP_UNIT_CHARS:
        return False
    return text[-LOOP_TAIL_CHARS:].count(unit) >= LOOP_REPEATS

def fly_probe(t, prompt, at_toks):
    """Worker: one greedy non-streamed probe. conf = geometric mean over ONLY
    the answer tokens inside {...} (punctuation ~0.99 dilutes the blended mean
    upward); "blended" keeps the all-token score for comparison. Hitting the
    "</think>" stop string = ended_with_think. A failed probe is skipped."""
    body = {"model": MODEL, "prompt": prompt, "max_tokens": PROBE_MAX_TOK,
            "temperature": 0.0, "logprobs": 1, "stop": ["</think>"]}
    try:
        r = SESSION.post(f"{SERVER}/v1/completions", json=body, timeout=90)
        r.raise_for_status()
        ch = r.json()["choices"][0]
        lp = ch.get("logprobs") or {}
        toks = lp.get("tokens") or []
        tlps = lp.get("token_logprobs") or []
        text = ch.get("text") or ""
        blended = float(np.exp(np.mean(tlps))) if tlps else 0.0
        i0, i1 = text.find("{"), text.find("}", max(text.find("{"), 0))
        ans_lps, pos = [], 0
        for tk, l in zip(toks, tlps):
            s, e = pos, pos + len(tk)
            pos = e
            if i0 >= 0 and i1 > i0 and e > i0 + 1 and s < i1 and l is not None:
                ans_lps.append(l)
        conf = float(np.exp(np.mean(ans_lps))) if ans_lps else blended
        events.put((t, {"kind": "probe", "at": at_toks, "text": text,
                        "conf": conf, "blended": blended, "ntok": len(tlps),
                        "ewt": ch.get("finish_reason") == "stop"}, None))
    except Exception as e:
        events.put((t, {"kind": "probe", "at": at_toks, "failed": str(e),
                        "text": "", "conf": 0.0, "blended": 0.0,
                        "ntok": 0, "ewt": False}, None))

def launch_probe(t):
    """Main thread only. Snapshot the trace and fork its graduation probe."""
    t.probing = True
    t.last_probe_at = t.toks_gen
    executor.submit(fly_probe, t, t.prompt_text + t.gen_text + PROBE_TEXT, t.toks_gen)

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
    """Main thread only. One streaming leg: the whole remaining budget.
    Judgment happens live."""
    budget = MAX_TOK_TRACE - t.toks_gen
    t.kill = threading.Event()
    t.pending = None
    inflight.add(t.id)
    executor.submit(fly_stream, t, t.prompt_text + t.gen_text, max(budget, 1))

def judge(t, scores):
    """Track the lifetime low; judge REPLACEMENTS against the armed bar.
    Wave 1 (ids < SEATS) runs bar-free — its finishers ARE the calibration.
    One dip below the bar = instant cut.
    Returns the verdict: None (safe) | 'cut'."""
    if scores and min(scores) < t.judge_min:
        t.judge_min = min(scores)
    if t.id < SEATS or bar is None:
        return None
    for sc in scores:
        if sc < bar:
            return "cut"
    return None

# ---------------- voting helpers (used once per question, after its run) ----------------
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

# ==================== THE SWEEP: one run per question ====================
for QID in QIDS:
    # the new arms go in the filename so a sweep never overwrites its own results
    _extras = (("_cs" if PROBE_EVERY > 0 else "")
               + (f"_loop{LOOP_ACTION[0]}" if LOOP_ACTION != "off" else ""))
    save_path = f"{OUT_DIR}/{DS_TAG}q{QID}_bar{_extras}.pkl"
    # aime25 runs saved before the prefix existed are bare q<N>_ — still done
    _legacy = f"{OUT_DIR}/q{QID}_bar{_extras}.pkl" if DATASET == "aime25" else None
    _done = next((p for p in (save_path, _legacy) if p and os.path.exists(p)), None)
    if _done:
        print(f"Q{QID}: already saved ({_done}) — skipping")
        continue

    print(f"\n{'=' * 60}\n### Q{QID}  ({(time.time() - t_sweep) / 60:.0f} min into the sweep)\n{'=' * 60}")
    question, ground_truth = data[QID]["question"], str(data[QID]["answer"]).strip()
    if FORCE_BOXED:
        question += "\n\nPlease put your final answer within \\boxed{}."
    print(f"Q{QID}: {question[:80]}...\nGround truth: {ground_truth}\n")
    BASE_PROMPT = render_chat(question)

    # -------- fresh run state (mutated ONLY by the main thread) --------
    traces    = [Trace(i) for i in range(SEATS)]
    launched  = SEATS
    bar       = None             # armed by update_bar() at BAR_MIN_CALIBRATORS finishers
    LINE_HISTORY = []            # game tape: the bar at every update, for the figure
    t_start   = time.time()
    events    = queue.Queue()    # (trace, payload|None, error|None) from worker threads
    inflight  = set()
    run_over = False
    n_events  = 0

    # -------- the run loop: stream in, judge live --------
    print(f"Run start: {SEATS} seats (cap {MAX_TRACES}), streaming (report every "
          f"{STREAM_BATCH} tokens) | wave 1 line-free; replacements face the "
          f"self-calibrating bar (keep top {BAR_KEEP_TOP}%, arms at "
          f"{BAR_MIN_CALIBRATORS} finishers, updates per finisher)"
          + (f" | probes every {PROBE_EVERY} (graduate at {GRAD_CONF})"
             if PROBE_EVERY > 0 else "")
          + (f" | loop guard ON ({LOOP_ACTION})" if LOOP_ACTION != "off" else "")
          + f" | close: landslide ({CONSENSUS:.0%}) OR certificate")
    for t in traces:
        launch(t)

    while inflight:
        t, payload, err = events.get()
        n_events += 1

        # ---- graduation-probe verdicts ----
        if payload is not None and payload.get("kind") == "probe":
            t.probing = False
            t.probe_toks += payload["ntok"]
            if "failed" in payload:
                print(f"Trace {t.id}: probe failed at {payload['at']} tokens "
                      f"({payload['failed'][:60]}) — skipped")
                continue
            p_ans = extract_answer("\\boxed" + payload["text"])
            rec = {"at": payload["at"], "conf": payload["conf"],
                   "blended": payload["blended"],
                   "ewt": payload["ewt"], "answer": p_ans}
            t.probes.append(rec)
            # graduate on ONE perfect probe: sure + closing + a real answer
            if (t.pending is None and not run_over and t.status == "running"
                    and rec["conf"] >= GRAD_CONF and (rec["ewt"] or not GRAD_EWT)
                    and p_ans is not None):
                t.grad_answer = p_ans
                t.pending = "graduate"
                t.kill.set()
                print(f"Trace {t.id}: GRADUATED at {payload['at']} tokens — "
                      f"conf {rec['conf']:.3f}, answer {p_ans}")
            continue

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
            t.confs += payload["scores"]
            if t.pending is None and not run_over:
                verdict = judge(t, payload["scores"])
                if verdict is not None:
                    t.pending = verdict
                    t.kill.set()                              # stream closes within a chunk
            # the loop guard
            if (LOOP_ACTION != "off" and t.pending is None and not run_over
                    and t.toks_gen - t.last_loop_check >= LOOP_CHECK_EVERY):
                t.last_loop_check = t.toks_gen
                if looping(t.gen_text):
                    t.looped = True
                    t.pending = "cut"
                    t.kill.set()
                    print(f"Trace {t.id}: LOOPING at {t.toks_gen} tokens "
                          f"(tail unit repeats >= {LOOP_REPEATS}x) -> ended, no ballot")
            # the probe: fixed schedule, nothing else
            if (PROBE_EVERY > 0 and not t.probing and t.pending is None
                    and not run_over and t.toks_gen >= PROBE_MIN_TOKS
                    and t.toks_gen - t.last_probe_at >= PROBE_EVERY):
                launch_probe(t)
            continue                                          # trace still in flight
        else:                                                 # "end": the leg is over
            inflight.discard(t.id)
            t.gen_text += payload["text"]; t.toks_gen += payload["ntok"]
            fin = payload["finish"]
            t.confs += payload["scores"]
            if t.pending is None and not run_over and payload["scores"]:
                verdict = judge(t, payload["scores"])
                if verdict is not None:
                    t.pending = verdict

            ans = extract_answer(t.gen_text) if fin == "stop" else None

            if run_over:                                     # landed after the certificate
                t.status = "abandoned"
            elif t.pending == "graduate":                     # the probe called it home
                t.status, t.answer = "finished", t.grad_answer
                t.graduated = True
                print(f"Trace {t.id}: finished EARLY at {t.toks_gen} tokens "
                      f"(graduation probe) | answer={t.answer}")
            elif t.pending == "cut":                          # the bar (or the loop guard)
                t.status = "stopped"
                if t.looped:
                    print(f"Trace {t.id}: loop ended at {t.toks_gen} tokens (no ballot)")
                else:
                    print(f"Trace {t.id}: cut at the bar "
                          + (f"{bar:.3f} " if bar is not None else "")
                          + f"(its low {t.judge_min:.3f}, {t.toks_gen} tokens)")
            elif ans is not None:                             # crossed the finish line
                t.status, t.answer = "finished", ans
                print(f"Trace {t.id}: finished at {t.toks_gen} tokens | answer={ans}")
            elif fin == "stop":                               # EOS without a boxed answer
                t.status = "truncated"
                print(f"Trace {t.id}: ended without a boxed answer at {t.toks_gen} "
                      f"tokens -> truncated")
            else:                                             # hit its budget
                t.status = "truncated"
                print(f"Trace {t.id}: truncated at {t.toks_gen} tokens (cap)")

        # ---- this trace departed: per-trace pit stop ----
        if t.status == "finished":
            update_bar()                                      # finishers calibrate
        if CONSENSUS <= 1.0 and not run_over:
            lead, share = consensus_check()
            n_fin = sum(1 for x in traces if x.status == "finished")
            if lead is not None and share >= CONSENSUS and n_fin >= 3:
                run_over = True
                live_ids = [x.id for x in traces if x.id in inflight]
                for x in traces:                              # drain INSTANTLY
                    if x.id in inflight:
                        x.kill.set()
                print(f"Consensus after {n_fin} finishers: '{lead}' holds {share:.0%} — "
                      f"killing {len(live_ids)} in-flight streams, no new launches")
        if not run_over:
            winner = certificate()
            if winner is not None:
                run_over = True
                live_ids = [x.id for x in traces if x.id in inflight]
                for x in traces:                              # drain INSTANTLY
                    if x.id in inflight:
                        x.kill.set()
                print(f"CERTIFICATE: '{winner}' cannot be caught "
                      f"(margin exceeds all {len(live_ids)} outstanding) — run over")
        if not run_over and launched < MAX_TRACES:
            nt = Trace(launched); traces.append(nt)
            print(f"Trace {launched}: seated (replacing {t.id})"
                  + (f" | bar {bar:.3f}" if bar is not None else " | bar unarmed"))
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

    probe_tokens = sum(t.probe_toks for t in done)
    total_tokens = sum(t.toks_gen for t in done) + probe_tokens  # EVERYTHING the
                                                       # GPU generated, probes included
    n_status     = lambda s: sum(1 for x in done if x.status == s)
    n_graduated  = sum(1 for t in done if t.graduated)
    n_looped     = sum(1 for t in done if t.looped)
    print("\n=== PeerConf Summary (streaming) ===")
    print(f"Final bar: {bar if bar is None else f'{bar:.3f}'} "
          f"(keep top {BAR_KEEP_TOP}% of finishers' minima) | "
          f"seats {SEATS} | launched {launched}/{MAX_TRACES} | events: {n_events}")
    print(f"Traces: finished {n_status('finished')} | stopped {n_status('stopped')} "
          f"| truncated {n_status('truncated')} | abandoned {n_status('abandoned')}")
    if PROBE_EVERY > 0:
        print(f"Graduation probes: {sum(len(t.probes) for t in done)} fired "
              f"({probe_tokens} probe tokens) | graduated early: {n_graduated}")
    if LOOP_ACTION != "off":
        print(f"Loop guard: {n_looped} loops caught and ended (no ballots cast)")
    print(f"Valid answers for voting: {len(voters)}")
    print(f"Final answer: {voting_results['majority'][0]}   | ground truth: {ground_truth}")
    print(f"Total tokens generated (traces + probes, incl. discarded): {total_tokens}"
          + (f" (of which probes: {probe_tokens})" if probe_tokens else ""))
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
                     "config": {"MODE": "server-stream", "MODEL": MODEL,
                                "DATASET": DATASET,
                                "BAR_KEEP_TOP": BAR_KEEP_TOP,
                                "BAR_MIN_CALIBRATORS": BAR_MIN_CALIBRATORS,
                                "WINDOW": WINDOW, "STREAM_BATCH": STREAM_BATCH,
                                "FORCE_BOXED": FORCE_BOXED,
                                "LOOP_ACTION": LOOP_ACTION,
                                "LOOP_CHECK_EVERY": LOOP_CHECK_EVERY,
                                "LOOP_UNIT_CHARS": LOOP_UNIT_CHARS,
                                "LOOP_TAIL_CHARS": LOOP_TAIL_CHARS,
                                "LOOP_REPEATS": LOOP_REPEATS,
                                "PROBE_EVERY": PROBE_EVERY,
                                "PROBE_MAX_TOK": PROBE_MAX_TOK,
                                "PROBE_MIN_TOKS": PROBE_MIN_TOKS,
                                "GRAD_CONF": GRAD_CONF,
                                "GRAD_EWT": GRAD_EWT,
                                "SEATS": SEATS, "MAX_TRACES": MAX_TRACES,
                                "CONSENSUS": CONSENSUS,
                                "final_bar": bar},
                     "voting": voting_results, "tokens": total_tokens,
                     "time_s": round(time.time() - t_start, 2),
                     "probe_tokens": probe_tokens,
                     "launched": launched,
                     "line_history": LINE_HISTORY,
                     "mins": {t.id: t.judge_min for t in done if t.confs},
                     "traces": [{"id": t.id, "status": t.status, "answer": t.answer,
                                 "toks_gen": t.toks_gen,
                                 "confs": t.confs,
                                 "looped": t.looped,
                                 "graduated": t.graduated,
                                 "probes": t.probes,
                                 "probe_toks": t.probe_toks,
                                 "text": t.gen_text,
                                 "prompt": t.prompt_text} for t in done]}, f)
    print(f"Saved to {save_path}")

print(f"\nSweep over: {len(list(QIDS))} questions requested, "
      f"{(time.time() - t_sweep) / 60:.0f} min total")
