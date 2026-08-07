# ======================= CELL 2 — THE RACE (v4 streaming belt) =======================
import json, re, time, pickle, os, queue, threading
import numpy as np, requests
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from transformers import AutoTokenizer
from dynasor.core.evaluator import math_equal

# ==================== PeerConf CONTROL PANEL ====================

MODEL   = "Qwen/Qwen3-8B"
SERVER  = "http://localhost:8000"

QID            = 6        # which AIME problem to run (0-29)
SEATS          = 16       # traces in flight at once — the belt's chairs
MAX_TRACES     = 32       # total launch cap. A departed trace frees its seat for a
                          # fresh one until this cap — or the landslide rule ends the
                          # race first (CONSENSUS below).

# ----- the line (quantile of per-trace WORST MOMENTS, judged live) -----
CONFIDENCE_PERCENTILE = 95  # DeepConf's exact dial (repo arg name + semantics):
                            # the KEEP-percent. line = np.percentile(per-trace
                            # minima, 100 - this).
                            #   90 = keep top 90% of the field, cut only the worst
                            #        ~10% (the arm that survives being made live)
                            #   10 = keep top 10% (DeepConf-low). VERIFIED
                            #        2026-07-26: live rank-at-birth = noise. Don't
                            #        run live without a rethink.
                            # Structural guarantee: the best trace's minimum is
                            # always >= the line; a zero-finisher wipeout is
                            # impossible by construction.
# ----- LINE_MODE: how the line is drawn (peerconf/reflect arms only) -----
LINE_MODE = os.environ.get("LINE_MODE", "percentile")
                          # "percentile" = the dial above: np.percentile of the live
                          #                minima bucket (the original PeerConf line)
                          # "conformal"  = same-age conformal rank: trace at age A is
                          #                judged against the k-th worst of its peers'
                          #                worst-moment-at-age-A (tape lookup), where
                          #                k = floor(DELTA * (jury+1)). Exchangeability
                          #                gives the exact guarantee: a healthy trace
                          #                falls below this line with prob <= DELTA.
                          #                If k < 1 the jury is too small to certify
                          #                DELTA -> judgment suspends (free run): the
                          #                jury floor and the frontier rule fall out
                          #                of the same arithmetic, no extra dial.
DELTA = float(os.environ.get("DELTA", "0.0625"))
                          # the error budget: max probability of cutting a healthy
                          # trace. 0.0625 = 1/16 -> with a 15-peer jury, k=1, the
                          # line is the single worst peer. Cut traces leave the jury;
                          # finished/truncated peers stay (frozen at lifetime worst).
WINDOW         = 2048     # sliding window: a token's score = avg confidence of its
                          # last 2048 tokens (Meta's value). FULL windows only —
                          # partial-window means are startup noise (the 13.6 artifact).
STREAM_BATCH   = 1        # v4: tokens are STREAMED. Every STREAM_BATCH tokens the
                          # worker reports in and the main thread runs
                          # pour -> redraw -> judge. At 1, judgment is TOKEN-EXACT:
                          # a cut lands at the crossing, DeepConf-checker semantics
                          # on a stock server. (judge_min is O(1), line history
                          # records only changes, so 1 is cheap.)
DWELL_TOKENS   = 128      # sustained crossing required. 2026-07-30: the Q6 first
                          # flight birth-cut two newborns at token 2049 on 0.002-0.003
                          # margins — dwell=1 made first-window noise fatal; 128 is
                          # the middle of the 64-256 range from that post-mortem.
                          # (deepconf/rc arms bypass dwell anyway: instant at their
                          # frozen matured bar, exactly their semantics.)
# Judgment starts the moment a trace has poured its first full window (token
# 2048): pour precedes judge, and DeepConf's own window-fill guard has the same
# floor. No extra grace: the lap belt's 4096 floor was a lap-boundary artifact.

# ----- the response (what happens when a trace is judged below the line) -----
DIP_ACTION     = "stop"    # "stop"    = cut, DeepConf-style: stream closed, no relaunch
                           # "reflect" = RC-style reflection prompt; the trace
                           #             continues and can still vote (PeerConf)
STOP_ON_RELAPSE = False    # (only used when DIP_ACTION="reflect")
                           # False = reflected traces run unjudged to the end and vote
                           # True  = reflected traces stay judged on their POST-
                           #         reflection scores; a second dip = cut

# ----- the final check (the blind-spot guard) -----
FINAL_CHECK    = "wait"   # 2026-07-30 decision: "wait" is the guard; the selfcheck
                          # audit prompt is retired (too heavy, steers the trace).
                          # fires ONCE per trace, the moment it boxes an answer,
                          # BEFORE that answer is accepted for the election:
                          #   "off"       = no second look — answer stands
                          #   "wait"      = splice "Wait" into the trace's own text
                          #                 (Self-Correction Bench, arXiv:2507.02778)
                          #   "selfcheck" = splice an explicit re-verify instruction
FINAL_CHECK_TOKENS = 4000 # token cap for the verification leg (streamed like any
                          # leg, but never judged)
FORCE_BOXED    = False    # True = append "Please put your final answer within
                          # \boxed{}." to the prompt.

# ----- early stopping (the landslide rule) -----
CONSENSUS      = 0.95     # the landslide rule, ON at DeepConf's tau (B.1: 0.95 =
                          # best tradeoff). Checked after EVERY finished trace; if
                          # the leading answer holds this share of the weighted votes
                          # among finished traces (and >=3 have finished; 2026-07-27:
                          # back to 3 per spec — accepting the false-landslide risk), stop
                          # launching AND kill the in-flight streams on the spot —
                          # v4 drains instantly instead of letting laps run out.
                          # 2.0 = DISABLED (share caps at 1.0) — the
                          # DeepConf-as-released-symmetric arm.

# ----- generation (same dials as the DeepConf baseline) -----
TEMPERATURE    = 0.6
TOP_P          = 0.95
TOP_K          = 20
LOGPROBS       = 20       # top-20 candidates per token — the confidence data
MAX_TOK_TRACE  = 30000    # total generation cap per trace, counted in tokens GENERATED

# NOTE (text space): we continue traces in TEXT space over HTTP (prompt = rendered
# template + text so far). The server re-tokenizes on each leg — a continuation
# boundary can occasionally split what was one token into two. Harmless for
# reasoning; noted for exactness. v4 legs are rare (one per trace life stage:
# race leg, reflection leg, verification leg), so this matters even less than v3.
# ================================================================

# OUT_DIR: Colab CELL 1 defines it in this namespace (Drive path); standalone runs
# (Modal / Lightning / local) fall back to the OUT_DIR env var, then ./peerconf_out
OUT_DIR = globals().get("OUT_DIR") or os.environ.get("OUT_DIR", "peerconf_out")

# ---- the three arms: which method is this run? ----
ARM = os.environ.get("ARM", "peerconf")   # peerconf | deepconf | rc | reflect
if ARM == "reflect":                       # arm 4: FULL PeerConf stack (live line,
    DIP_ACTION = "reflect"                 # dwell, guard, landslide) but a dip gets
                                           # the fresh RC rescue prompt (UNARMED:
                                           # the reflected trace is never judged
                                           # again) instead of the cut
elif ARM == "rc":                          # arm 3: Reflective Confidence — EXACTLY
    DIP_ACTION = "reflect"                 # DeepConf (warmup -> frozen bar -> instant
    FINAL_CHECK = "off"                    # trigger) but the response is the RC
                                           # splice (fresh prompt restating question +
                                           # partial reasoning) instead of the cut
elif ARM == "deepconf":                    # arm 1: DeepConf as released + their
    DIP_ACTION = "stop"                    # paper's consensus stopping added
    FINAL_CHECK = "off"                    # no guard in their method
WARMUP_N = SEATS          # deepconf/rc arms: the first 16 traces run unjudged to full
                          # completion (their offline warmup), then the bar freezes
warmup_done = (ARM not in ("deepconf", "rc"))
frozen_line = None

tok    = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
EOS_ID = tok.eos_token_id

_aime_paths = ["aime25.jsonl", os.path.join("benchmarks", "aime25.jsonl"),
               os.path.join("..", "benchmarks", "aime25.jsonl")]
try:
    _aime_paths.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "benchmarks", "aime25.jsonl"))
except NameError:
    pass                                   # exec'd without __file__ (Modal)
with open(next(p for p in _aime_paths if os.path.exists(p))) as f:
    data = [json.loads(l) for l in f]
question, ground_truth = data[QID]["question"], str(data[QID]["answer"]).strip()
if FORCE_BOXED:                        # question feeds the main prompt AND the reflection prompt
    question += "\n\nPlease put your final answer within \\boxed{}."
print(f"Q{QID}: {question[:80]}...\nGround truth: {ground_truth}\n")

def render_chat(user_text):
    return tok.apply_chat_template([{"role": "user", "content": user_text}],
                                   tokenize=False, add_generation_prompt=True)

BASE_PROMPT = render_chat(question)

FINAL_CHECK_TEXT = {
    "wait":      "\nWait",
    "selfcheck": ("\n\nBefore I commit to that answer, let me audit the STRUCTURE "
                  "of my solution, not just the arithmetic. First, my case analysis: "
                  "let me explicitly list every case I counted, then actively try to "
                  "construct a configuration that fits none of them, or one that I "
                  "dismissed without proof. An omitted case is the most dangerous "
                  "error, because every later step inherits it silently. Second, the "
                  "final computation. If I find a missing case or an error, I will "
                  "redo the count and give the corrected final answer in \\boxed{}; "
                  "if everything truly holds, I will restate the same final answer "
                  "in \\boxed{}."),
}

SESSION = requests.Session()

def build_reflect_prompt(path_text):
    """RC's exact fresh-prompt structure and wording, third-person framing."""
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
        self.prompt_text = BASE_PROMPT  # replaced by the fresh RC prompt on reflection
        self.gen_text  = ""      # generated text for the CURRENT prompt
        self.confs     = []      # full-window score per token (whole life)
        self.cummin    = []      # the tape: worst-so-far at every age (cummin[a] =
                                 # min of confs[:a+1]) — same-age jury lookups for
                                 # LINE_MODE="conformal". Appended in lockstep with
                                 # confs; O(1) per token, derivable but kept live.
        self.last_line = None    # this trace's last recorded line (conformal lines
                                 # are per-trace; history records per-trace changes)
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

# ---------------- shared race state (mutated ONLY by the main thread) ----------------
traces    = [Trace(i) for i in range(SEATS)]
launched  = SEATS
MINS      = {}                   # {trace id: its worst full-window score EVER} — one
                                 # entry per trace, never deleted (anchoring)
LINE_HISTORY = []                # game tape: the line at every pour, for the figure
t_start   = time.time()
events    = queue.Queue()        # (trace, payload|None, error|None) from worker threads
inflight  = set()
race_over = False
n_events  = 0
line_live = False
last_line = None                 # LINE_HISTORY records only line CHANGES, so the
                                 # game tape stays small even at STREAM_BATCH = 1
executor  = ThreadPoolExecutor(max_workers=SEATS + 4)

def current_line():
    """peerconf/reflect: DeepConf's bar formula over LIVE per-trace minima, None until
    every opening seat has poured once. deepconf/rc arms: the FROZEN warmup bar.
    LINE_MODE="conformal" has no single global line (it is per-trace, per-age) —
    this returns None there and conformal_line(t) is the judge."""
    if ARM in ("deepconf", "rc"):
        return frozen_line
    if LINE_MODE == "conformal":
        return None
    if len(MINS) < SEATS: return None
    return float(np.percentile(list(MINS.values()), 100 - CONFIDENCE_PERCENTILE))

def extend_tape(t, scores):
    """Append the batch to the trace's cummin tape (worst-so-far at every age).
    Main thread only, in lockstep with t.confs."""
    m = t.cummin[-1] if t.cummin else float("inf")
    for sc in scores:
        if sc < m: m = sc
        t.cummin.append(m)

def conformal_line(t):
    """The same-age conformal rank line for trace t at its current age.

    Jury = every other trace that has poured at least one full window and was not
    cut at the line ("stopped" leaves the jury; finished/truncated/abandoned peers
    serve forever, frozen at their lifetime worst). A peer that reached t's age
    testifies with its worst-moment AT THAT AGE (tape page t); a younger or
    finished peer testifies with its latest worst-so-far (the frontier fallback).

    line = k-th worst juror value, k = floor(DELTA * (jury+1)). Exchangeability:
    a healthy trace dips below the line with probability <= DELTA — exact, any N.
    k < 1 means the jury cannot certify DELTA -> None (judgment suspended, free
    run). The jury floor and frontier hands-off rule are this same arithmetic."""
    age = len(t.cummin)
    if age == 0:
        return None
    jury = []
    for x in traces:
        if x.id == t.id or x.status == "stopped" or not x.cummin:
            continue
        jury.append(x.cummin[min(age, len(x.cummin)) - 1])
    k = int(DELTA * (len(jury) + 1))
    if k < 1:
        return None
    return float(sorted(jury)[k - 1])

def consensus_check():
    # Paper Sec 4.1: ALL completed traces vote, weighted by lowest group
    # confidence; the top-eta filter only sets the termination bar s
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
                if len(win) == WINDOW:            # full windows only — DeepConf's rule
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
    if scores:
        m = min(scores)
        if t.id not in MINS or m < MINS[t.id]:
            MINS[t.id] = m
        if m < t.judge_min:
            t.judge_min = m
    if LINE_MODE == "conformal" and ARM not in ("deepconf", "rc"):
        line = conformal_line(t)
    else:
        line = current_line()
    if line is None:
        return None
    global line_live, last_line
    if not line_live:
        line_live = True
        print(f"Line live at {line:.3f} "
              + (f"(conformal, delta={DELTA:g})" if LINE_MODE == "conformal"
                 else f"({len(MINS)} trace minima)"))
    if LINE_MODE == "conformal":
        if line != t.last_line:          # per-trace tape: conformal lines differ by age
            t.last_line = line
            LINE_HISTORY.append({"tid": t.id, "line": line,
                                 "n_traces": len(MINS), "t": time.time() - t_start})
    elif line != last_line:
        last_line = line
        LINE_HISTORY.append({"tid": t.id, "line": line,
                             "n_traces": len(MINS), "t": time.time() - t_start})
    judged = (DIP_ACTION == "stop") or (not t.reflected) or STOP_ON_RELAPSE
    if not judged:
        return None
    if ARM in ("deepconf", "rc"):     # their semantics: instant at the frozen bar
        for sc in scores:             # (rc = same trigger, reflect instead of cut)
            if sc < line:
                return "cut" if ARM == "deepconf" else "reflect"
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

# ---------------- the streaming belt: pour -> redraw -> judge, live ----------------
LINE_TAG = (f"cd{int(round(DELTA * 10000))}"
            if LINE_MODE == "conformal" and ARM not in ("deepconf", "rc")
            else f"p{CONFIDENCE_PERCENTILE}")
print(f"Race start: {SEATS} seats, streaming (report every {STREAM_BATCH} tokens), "
      + (f"conformal line (delta={DELTA:g}: k-th worst same-age peer, "
         f"k=floor(delta*(jury+1)), k<1 -> free run)" if LINE_MODE == "conformal"
         else f"keep top {CONFIDENCE_PERCENTILE}% (line = "
              f"{100 - CONFIDENCE_PERCENTILE}th pct of minima)"))
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
            extend_tape(t, payload["scores"])
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
            extend_tape(t, payload["scores"])
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
    # Alg. 2 order: freeze the bar FIRST, check beta SECOND, and only launch
    # the online wave if consensus hasn't already settled the race
    just_armed = False
    if ARM in ("deepconf", "rc") and not warmup_done:
        if not any(x.id in inflight for x in traces[:WARMUP_N]):
            warmup_done = True
            just_armed = True
            wmins = [MINS[i] for i in range(WARMUP_N) if i in MINS]
            frozen_line = float(np.percentile(wmins, 100 - CONFIDENCE_PERCENTILE))
            print(f"Warmup done: bar frozen at {frozen_line:.3f} "
                  f"({len(wmins)} complete traces)")
    if CONSENSUS <= 1.0 and not race_over:
        lead, share = consensus_check()
        n_fin = sum(1 for x in traces if x.status == "finished")
        if (lead is not None and share >= CONSENSUS
            and (warmup_done if ARM in ("deepconf", "rc") else n_fin >= 3)):
            race_over = True
            live_ids = [x.id for x in traces if x.id in inflight]
            for x in traces:                              # v4: drain INSTANTLY
                if x.id in inflight:
                    x.kill.set()
            print(f"Consensus after {n_fin} finishers: '{lead}' holds {share:.0%} — "
                  f"killing {len(live_ids)} in-flight streams, no new launches")
    if just_armed:
        if race_over:
            print("Consensus already held at warmup — online wave skipped")
        else:
            print("Launching the armed budget")
            while launched < MAX_TRACES and len(inflight) < SEATS:
                nt = Trace(launched); traces.append(nt)
                launched += 1
                launch(nt)
    elif warmup_done and not race_over and launched < MAX_TRACES:
        nt = Trace(launched); traces.append(nt)
        nl = current_line()
        print(f"Trace {launched}: seated (replacing {t.id})"
              + (f" | line now {nl:.3f}" if nl is not None else ""))
        launched += 1
        launch(nt)

# ---------------- results + DeepConf-style voting table ----------------
done   = traces
voters = [t for t in done if t.status == "finished" and t.answer is not None]

def trace_measures(t):
    c = np.array(t.confs) if t.confs else np.array([0.0])
    k = max(1, int(len(c) * 0.10))
    return {"mean_conf":     float(c.mean()),
            "tail_conf":     float(c[-1]),
            "bottom_window": float(np.sort(c)[:k].mean()),
            "min_window":    float(c.min())}

M = {t.id: trace_measures(t) for t in voters}

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
print("\n=== DeepConf Summary (v4 — streaming belt) ===")
print(f"Frozen bar: {final_line if final_line is None else f'{final_line:.3f}'} "
      f"(keep top {CONFIDENCE_PERCENTILE}% of the {WARMUP_N}-trace warmup minima) | "
      f"seats {SEATS} | launched {launched}/{MAX_TRACES} | events: {n_events}")
print(f"Traces: finished {n_status('finished')} | cut at the bar {n_status('stopped')} "
      f"| truncated {n_status('truncated')} | abandoned {n_status('abandoned')}")
print(f"Valid answers for voting: {len(voters)}")
print(f"Final answer (lowest-window weighted vote, the paper's online rule): "
      f"{voting_results['min_window_weighted'][0]} | ground truth: {ground_truth}")
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

# ---------------- save (results + game-tape curves) ----------------
os.makedirs(OUT_DIR, exist_ok=True)
with open(f"{OUT_DIR}/q{QID}_{ARM}_{DIP_ACTION}_{FINAL_CHECK}_{LINE_TAG}_c{int(CONSENSUS*100)}_v4.pkl", "wb") as f:
    pickle.dump({"qid": QID, "gt": ground_truth,
                 "config": {"MODE": "server-stream-belt-v4", "ARM": ARM, "MODEL": MODEL,
                            "LINE_MODE": LINE_MODE, "DELTA": DELTA,
                            "LINE_IMPL": "trace-minima-stream",
                            "CONFIDENCE_PERCENTILE": CONFIDENCE_PERCENTILE,
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
                 "time_s": round(time.time() - t_start, 2),
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
print(f"Saved to {OUT_DIR}/q{QID}_{ARM}_{DIP_ACTION}_{FINAL_CHECK}_{LINE_TAG}_c{int(CONSENSUS*100)}_v4.pkl")
