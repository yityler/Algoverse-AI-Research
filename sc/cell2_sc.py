# ============ CELL 2 — SC@N BASELINE (self-consistency, unmanaged) ============
# Plain self-consistency: N independent traces per question, none of them judged,
# cut, probed or stopped early, then a majority vote over their final answers.
#
# This is the control the other two arms are measured against. It deliberately
# has NO bar, NO graduation probe, NO consensus close and NO loop guard: every
# trace runs to its natural stop or to MAX_TOK_TRACE, whichever comes first.
# That is the whole point — it is what the managed arms are saving tokens
# against, so anything that ends a trace early would make it a different method.
#
# Everything that decides an ANSWER is taken verbatim from the DeepConf arm
# (extract_answer, tidy_tex, same_answer, ballot_key) so the three arms are
# graded identically and the comparison is apples to apples. cell2 runs a whole
# sweep on import and cannot be imported from, so the copy is the only way to
# share the logic — the same reason cell3 keeps a copy. If the grading in
# deepconf/cell2_deepconf.py changes, change it here too.
#
# Loops over every question in QIDS: one run per question, one pkl per question.
# A question whose pkl already exists in OUT_DIR is skipped, so an interrupted
# sweep resumes with a simple rerun (delete a pkl to redo that question).
import json, re, time, pickle, os, queue, threading
import numpy as np, requests
from concurrent.futures import ThreadPoolExecutor
from transformers import AutoTokenizer
from dynasor.core.evaluator import math_equal

MODEL   = os.environ.get("MODEL", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")
SERVER  = "http://localhost:8000"
OUT_DIR = globals().get("OUT_DIR") or os.environ.get("OUT_DIR", "sc_out")
DATASET = os.environ.get("DATASET", "aime25")   # aime25 | math500 | gsm8k | hmmt25

# which questions to run. SC_QIDS lets the harness pilot a couple of questions
# without editing this file; unset means the full sweep.
QIDS           = range(30)
if os.environ.get("SC_QIDS"):
    QIDS = [int(x) for x in os.environ["SC_QIDS"].split(",") if x.strip()]
TOTAL_TRACES   = 32     # the N in SC@N. Every one of them runs unmanaged.
WAVE_SIZE      = 16     # how many are in flight at once. 32 traces at a 64k cap
                        # want ~2.05M tokens of KV; the box measured 1.67M, so
                        # 32-wide would queue inside vLLM. Two waves of 16 keep
                        # the batch inside the cache and match the shape the
                        # DeepConf warmup already ran at on this hardware.
                        # It changes nothing about the method: the traces are
                        # independent, so when they run cannot affect the vote.

TEMPERATURE    = 0.6
TOP_P          = 0.95
TOP_K          = -1
MAX_TOK_TRACE  = 64000    # total generation cap per trace, counted in tokens GENERATED

# SC reads nothing but the final answer, so the per-token top-20 logprobs the
# other two arms stream for their confidence window are pure overhead here.
# Asking for none does not change sampling or token counts, only how much JSON
# comes back over the wire.
LOGPROBS       = None

# ----- why this arm seeds and the other two do not -----
# Measured on this stack: the same prompt sent as a batch of 16 unseeded requests
# came back as the SAME 16 completions on two separate runs, in a different order.
# vLLM is reproducible per batch slot, so "unseeded" here does not mean
# "independent". SC@32 run as two waves of 16 would then draw the same 16 answers
# twice and report them as 32 votes -- an SC@16 result wearing an SC@32 label,
# with every pile exactly doubled and the winner unchanged.
# One distinct seed per trace makes the 32 draws genuinely independent and the
# run reproducible. It does not change the sampling DISTRIBUTION (same
# temperature and top-p), only which sample each trace draws from it.
# SEED_BASE keeps seeds distinct across questions as well as across traces.
SEED_BASE      = 1_000_003        # prime, so QID*SEED_BASE + tid never collides

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)

_bench = f"{DATASET}.jsonl"
_bench_paths = [_bench, os.path.join("benchmarks", _bench),
                os.path.join("..", "benchmarks", _bench)]
try:
    _here = os.path.dirname(os.path.abspath(__file__))
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

DS_TAG = f"{DATASET}_"
print(f"Benchmark: {DATASET} — {len(data)} questions from {_bench_path}, "
      f"running {len(QIDS)}")

SESSION = requests.Session()

_WS = re.compile(r"\s+")


def tidy_tex(a):
    """Cosmetic LaTeX only. Same value, fewer ways to write it. This exists
    because math_equal parses some renderings and not others: a ",\\ " separator
    between two roots defeats it even though ", " is fine."""
    s = str(a)
    for x, y in ((r"\dfrac", r"\frac"), (r"\tfrac", r"\frac"),
                 (r"\left", ""), (r"\right", ""),
                 (r"\!", ""), (r"\,", " "), (r"\;", " "), (r"\ ", " ")):
        s = s.replace(x, y)
    return _WS.sub(" ", s).strip()


def same_answer(a, b):
    """Do these two strings name the same value? Cheap tests first, then
    math_equal, which is what catches 0.5 against \\frac{1}{2}. It does not
    rationalise, so 9/\\sqrt{23} and 9\\sqrt{23}/23 stay apart."""
    if a is None or b is None:
        return False
    a, b = tidy_tex(a), tidy_tex(b)
    if a == b or _WS.sub("", a) == _WS.sub("", b):
        return True
    try:
        return bool(math_equal(a, b))
    except Exception:
        return False


def ballot_key(piles, ans):
    """The pile this answer belongs in. Equivalent answers share a pile, so the
    vote counts values rather than spellings."""
    for k in piles:
        if same_answer(ans, k):
            return k
    return str(ans)


def is_correct(ans, gt):
    if ans is None: return False
    return same_answer(ans, gt)


def extract_answer(text):
    """DeepConf's own extractor (facebookresearch/deepconf, deepconf/utils.py),
    so both arms read answers exactly the way the baseline does. Counting braces
    reads a nested \\boxed{\\dfrac{a}{b}}, which a [^{}] regex cannot. Empty
    comes back as None, not "", because callers test `is not None`."""
    if "boxed" not in text:
        return None
    ans = text.split("boxed")[-1]
    if not ans:
        return None
    if ans[0] == "{":
        stack, a = 1, ""
        for c in ans[1:]:
            if c == "{":
                stack += 1
                a += c
            elif c == "}":
                stack -= 1
                if stack == 0:
                    break
                a += c
            else:
                a += c
    else:
        a = ans.split("$")[0].strip()
    return a.strip() or None

class Trace:
    def __init__(self, tid, seed):
        self.id       = tid
        self.seed     = seed
        self.gen_text = ""
        self.toks_gen = 0
        self.retried  = False
        self.status   = "running"     # running|finished|truncated
        self.answer   = None


def fly_stream(t, prompt_text, max_toks):
    """One streamed request. No kill switch and no judging: nothing in SC can
    end a trace early, so the stream is read until the server closes it. The
    prompt and budget are arguments so a retry picks up from what the trace
    already generated instead of paying for it twice."""
    body = {"model": MODEL, "prompt": prompt_text, "max_tokens": int(max_toks),
            "temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K,
            "seed": t.seed, "stream": True}
    if LOGPROBS:
        body["logprobs"] = LOGPROBS
    try:
        r = SESSION.post(f"{SERVER}/v1/completions", json=body, stream=True, timeout=7200)
        r.raise_for_status()
        fin = None
        for raw in r.iter_lines():
            if not raw or not raw.startswith(b"data: "): continue
            payload = raw[6:]
            if payload == b"[DONE]": break
            ch = json.loads(payload)["choices"][0]
            text = ch.get("text") or ""
            # with logprobs off the response carries no per-token record, so the
            # token count comes from the tokenizer instead of len(top_logprobs)
            ntok = len((ch.get("logprobs") or {}).get("top_logprobs") or []) \
                if LOGPROBS else (len(tok.encode(text, add_special_tokens=False)) if text else 0)
            if ch.get("finish_reason"):
                fin = ch["finish_reason"]
            events.put((t, {"kind": "tok", "text": text, "ntok": ntok}, None))
        events.put((t, {"kind": "end", "finish": fin or "stop"}, None))
    except Exception as e:
        events.put((t, None, e))


def launch(t):
    inflight.add(t.id)
    budget = MAX_TOK_TRACE - t.toks_gen        # a first launch spends nothing yet
    executor.submit(fly_stream, t, PROMPT + t.gen_text, max(budget, 1))


def land(t, fin):
    """Read an answer off every trace whatever its stop reason, exactly as
    DeepConf does (deepconf/utils.py process_output) — a path that wrote its
    answer and THEN ran out of budget still casts a ballot."""
    ans = extract_answer(t.gen_text)
    if ans is not None:
        t.status, t.answer = "finished", ans
        print(f"Trace {t.id}: finished at {t.toks_gen} tokens | answer={ans}")
    else:
        t.status = "truncated"
        print(f"Trace {t.id}: ended without a boxed answer at {t.toks_gen} tokens "
              f"-> truncated ({fin})")


def drain(wave):
    while any(t.id in inflight for t in wave):
        t, payload, err = events.get()
        if err:
            inflight.discard(t.id)
            if not t.retried:
                t.retried = True
                print(f"Trace {t.id}: stream error, retrying ({err})")
                launch(t); continue
            t.status = "truncated"
            print(f"Trace {t.id}: stream failed twice -> truncated ({err})")
        elif payload["kind"] == "tok":
            t.gen_text += payload["text"]; t.toks_gen += payload["ntok"]
            continue
        else:
            inflight.discard(t.id)
            land(t, payload["finish"])


def majority(pool):
    """The SC vote: one ballot per trace, equivalent answers sharing a pile."""
    piles = {}
    for t in pool:
        k = ballot_key(piles, t.answer)
        piles[k] = piles.get(k, 0) + 1
    if not piles:
        return None, 0, piles
    a = max(piles, key=lambda k: piles[k])
    return a, piles[a], piles


executor = ThreadPoolExecutor(max_workers=WAVE_SIZE + 4)
os.makedirs(OUT_DIR, exist_ok=True)
t_sweep = time.time()

# ==================== THE SWEEP: one run per question ====================
for QID in QIDS:
    save_path = f"{OUT_DIR}/{DS_TAG}q{QID}_sc{TOTAL_TRACES}.pkl"
    if os.path.exists(save_path):
        print(f"Q{QID}: already saved ({save_path}) — skipping")
        continue

    print(f"\n{'=' * 60}\n### Q{QID}  ({(time.time() - t_sweep) / 60:.0f} min into the sweep)\n{'=' * 60}")
    question, ground_truth = data[QID]["question"], str(data[QID]["answer"]).strip()
    print(f"Q{QID}: {question[:80]}...\nGround truth: {ground_truth}\n")
    PROMPT = tok.apply_chat_template([{"role": "user", "content": question}],
                                     tokenize=False, add_generation_prompt=True)

    events   = queue.Queue()
    inflight = set()
    t_start  = time.time()
    traces   = []

    print(f"SC@{TOTAL_TRACES}: {TOTAL_TRACES} unmanaged traces in waves of "
          f"{WAVE_SIZE} | no bar, no probe, no consensus, no loop guard | "
          f"cap {MAX_TOK_TRACE} tokens/trace")
    for start in range(0, TOTAL_TRACES, WAVE_SIZE):
        wave = [Trace(i, QID * SEED_BASE + i)
                for i in range(start, min(start + WAVE_SIZE, TOTAL_TRACES))]
        traces += wave
        print(f"\n-- wave {start // WAVE_SIZE + 1}: traces {wave[0].id}-{wave[-1].id}")
        for t in wave: launch(t)
        drain(wave)

    total_tokens = sum(t.toks_gen for t in traces)
    voters = [t for t in traces if t.answer is not None]
    winner, votes, piles = majority(voters)

    # the check that says whether this is really SC@32 and not SC@16 twice
    n_distinct = len({t.gen_text for t in traces})
    if n_distinct < len(traces):
        print(f"!! WARNING: only {n_distinct} distinct completions among "
              f"{len(traces)} traces — the draws are NOT independent")

    n_fin = sum(1 for t in traces if t.status == "finished")
    n_tru = sum(1 for t in traces if t.status == "truncated")
    print(f"\n=== SC@{TOTAL_TRACES} Summary ===")
    print(f"Traces: finished {n_fin} | truncated {n_tru} | launched {len(traces)}")
    print(f"Distinct completions: {n_distinct}/{len(traces)}")
    print(f"Valid answers for voting: {len(voters)}")
    print(f"Vote spread: " + ", ".join(f"{k!r}:{v}" for k, v in
                                       sorted(piles.items(), key=lambda kv: -kv[1])[:6]))
    print(f"Final answer: {winner}   | ground truth: {ground_truth}")
    print(f"Total tokens: {total_tokens} | time: {time.time() - t_start:.2f}s")
    marks = f"majority:{'✓' if is_correct(winner, ground_truth) else '✗'}"
    print(f"Q{QID} done | gt={ground_truth} | {marks}")

    with open(save_path, "wb") as f:
        pickle.dump({"qid": QID, "gt": ground_truth,
                     "config": {"MODE": "sc-unmanaged", "MODEL": MODEL,
                                "DATASET": DATASET,
                                "TOTAL_TRACES": TOTAL_TRACES,
                                "WAVE_SIZE": WAVE_SIZE,
                                "MAX_TOK_TRACE": MAX_TOK_TRACE,
                                "TEMPERATURE": TEMPERATURE, "TOP_P": TOP_P,
                                "TOP_K": TOP_K, "LOGPROBS": LOGPROBS,
                                "SEED_BASE": SEED_BASE},
                     "n_distinct": n_distinct,
                     "voting": {"majority": (winner, None, len(voters))},
                     "vote_piles": piles,
                     "tokens": total_tokens,
                     "time_s": round(time.time() - t_start, 2),
                     "launched": len(traces),
                     "traces": [{"id": t.id, "seed": t.seed,
                                 "status": t.status, "answer": t.answer,
                                 "toks_gen": t.toks_gen,
                                 "confs": [],   # SC reads no confidence signal
                                 "text": t.gen_text,
                                 "prompt": PROMPT} for t in traces]}, f)
    print(f"Saved to {save_path}")

print(f"\nSweep over: {len(list(QIDS))} questions requested, "
      f"{(time.time() - t_sweep) / 60:.0f} min total")
