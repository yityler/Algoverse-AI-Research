# PeerConf run — Kaggle 2× T4, 2026-08-06

First run of PeerConf on hardware other than the author's. Model
`deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`, benchmark AIME25, questions 0 and 1.

**Settings were shrunk to fit two T4s** — 4 seats (not 16), 6 max traces (not 32),
15,000-token trace cap (not 30,000), 16,384 context. Everything else is Mofe's default,
including `LINE_TOP = 0.95`, `WINDOW = 2048`, `DWELL_TOKENS = 128`, `CONSENSUS = 0.95`,
`FINAL_CHECK = "wait"`, `TEMPERATURE = 0.6`. `WARMUP_MODE` was `False` throughout, so this
is plain PeerConf.

| | answer | truth | | tokens | wall clock | launched |
|---|---|---|---|---|---|---|
| Q0 | 70 | 70 | correct | 38,253 | 9.6 min | 6 |
| Q1 | 588 | 588 | correct | 75,101 | 22.7 min | 6 |

All seven voting methods agreed with the majority vote on both questions.

---

## 1. Validated

**The code reproduces off the author's machine.** Clean container, fresh install, correct
answers. PeerConf had not previously been run outside Mofe's environment.

**Every mechanism fires.** The confidence line goes live, weak traces get cut, seats
refill, the `wait` blind-spot guard fires, consensus stopping triggers, voting resolves,
results serialize to disk. None of this had been independently observed.

## 2. New observations

### 2.1 Consensus stopping is real, not hypothetical

On Q0 it fired after 3 finishers at 100% agreement, killed 1 in-flight stream and blocked
further launches. This matters for the DeepConf comparison: the plan is to add consensus
stopping to their code for fairness, and there is now an observed instance of it changing
a run rather than an assumption that it would.

### 2.2 Most generated tokens produced nothing

| | total tokens | reached an answer | wasted |
|---|---|---|---|
| Q0 | 38,253 | 24,095 | 37% |
| Q1 | 75,101 | 14,191 | **81%** |
| combined | 113,354 | 38,286 | **66%** |

Q1 breakdown: three traces hit the 15,000 cap (45,000 tokens, no answer), two were cut by
the line (15,910 tokens), and one trace carried the answer (14,191 tokens). One of six.

Q0 breakdown: three finishers (24,095), two cut by the line (6,785), one abandoned when
consensus fired (~7,373).

⚠️ **Confounded.** The 15,000-token cap is a concession to two T4s, not Mofe's setting. At
his 30,000 some truncated traces would likely have finished and the waste fraction would
drop. The finding is not "PeerConf wastes 66% of tokens" — it is that **waste fraction is
worth measuring as a first-class number**, because that is where the token cost lives and
it is not currently reported.

### 2.3 Cuts happen late

The four culled traces died at **2,176 / 4,609 / 4,921 / 10,989** tokens. The last had
already burned ~11k before the line caught it. Culling saves less than the intuition
suggests, and *tokens spent on traces later killed* belongs in the results table alongside
total tokens.

### 2.4 The `wait` guard was pure overhead on this sample

Fired 4 times, confirmed 4, revised 0, rescued 0, broke 0 — at a cost of roughly **2,570
tokens (~2% of the run)**. One trace spent 1,213 extra tokens confirming an answer it had
already boxed (8,591 → 9,804).

Small sample, and the guard exists to catch a failure mode that did not occur here. But
"does the guard pay for itself" is now a testable question with a measurement attached:
compare correction rate against its token cost across the full 30.

### 2.5 Per-question cost varies ~2× for the same outcome

38,253 vs 75,101 tokens, both correct, driven by whether consensus fired. Implication for
reporting: **mean tokens across questions will be noisy**. Report the distribution or
median, and report consensus-fire rate as a separate mechanism statistic rather than
letting it hide inside an average.

### 2.6 Minor

Confidence values run ~9,200–9,400 rather than 0–1, so `LINE_TOP` operates on a summed
scale. Worth stating explicitly in the paper so nobody reads the line position as a
probability.

## 3. Engineering findings

The dependency chain, which cost most of the setup time. Anyone reproducing this on fresh
hardware hits all three:

| Requirement | Why |
|---|---|
| `vllm==0.9.2` with `VLLM_USE_V1=0` | Current vLLM's V1 engine requires compute capability ≥ 8.0; T4 is 7.5. Fails at engine init with "Engine core initialization failed". 0.9.2 still ships the older engine. |
| `transformers==4.53.2` | vLLM 0.9.2 registers a config named `aimv2`; newer transformers already has one. Collision kills the server at startup. |
| Dynasor from `git+https://github.com/hao-ai-lab/Dynasor.git` | `cell2_race.py` imports `dynasor.core.evaluator.math_equal`. The PyPI package named `dynasor` is an unrelated project — it installs cleanly and then fails on the import. |

Working configuration on 2× T4 (16 GB each):

- 8B splits across both cards via `--tensor-parallel-size 2`, **7.66 GiB per card**
- `--dtype half` (Turing has no bfloat16)
- `--max-model-len 16384` with 4 seats fits; **4,096 is far too small** — every trace hit
  the cap before boxing an answer and there was nothing to vote on
- Kaggle needs **Internet: On** (phone verification) or pip and the model download fail
- Peak ~12.1 GiB per GPU, 25 GiB system RAM

## 4. Explicitly NOT established

- **Nothing about PeerConf vs DeepConf.** No baseline was run. The `WARMUP_MODE` switch in
  `cell2_race.py` is a frozen-line ablation of PeerConf, *not* an implementation of
  DeepConf, and should not be reported as one.
- **No accuracy claim.** n=2. 2/2 correct is not a 100% accuracy result.
- **No token claim.** Shrunken settings, and the cap truncated traces that would otherwise
  have finished.
- **Not reproducible run-to-run.** `TEMPERATURE = 0.6`, single seed. A rerun gives
  different numbers.

## 5. Suggested next steps

1. Full 30 questions at these settings (~5–8 h on 2× T4) — enough to get a distribution
   for §2.2 and §2.5 even though the cap still binds.
2. Move to a 48 GB card (AWS `ml.g6e.xlarge`, L40S) for Mofe's real settings, where the
   30,000-token cap removes the truncation confound.
3. Add *wasted tokens* and *consensus-fire rate* to the per-question output, so §2.2 and
   §2.5 are measured rather than reconstructed from the log.
