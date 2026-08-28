# MATH-500 — DeepSeek-R1-0528-Qwen3-8B, PeerConf-low (WINDOW = 256)

**All 500 questions, single arm, one implementation, one pass.**

The AIME25 and HMMT25 runs on this model are in [../../aime25](../../aime25/README.md)
and [../../hmmt25_deepseek](../../hmmt25_deepseek/README.md). Earlier, smaller
MATH-500 work is in [../math500_w2048](../math500_w2048/README.md) and
[../math500_w256](../math500_w256/README.md) — neither is comparable to this
page; see *No baseline* below.

## Results

| Method | Model | Dataset | Total tokens | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | DeepSeek-8B | MATH500 (Q0-499) | 24,738,575 | 91.0% | 49,477 |

Accuracy is the min-window-weighted vote, graded with `math_equal`, 455/500.
Tokens split 24,000,389 trace + 738,186 probe (probes are 2.98% of the total).

**No reduction percentage is quoted, because there is no baseline to quote it
against.** No other method and no other implementation has run all 500
questions in this repo. DeepConf has never completed MATH-500 here: it crashed
outright on the WINDOW=2048 attempt when every warm-up trace came in shorter
than the window. The 25-question PeerConf/DeepConf comparison in
[../math500_w256](../math500_w256/README.md) is a **different, older
implementation** with different probe settings, so a delta against it would
confound method with version and must not be presented as a saving.

Accuracy is stable across voting rules, which is a stronger result than HMMT25,
where the same arm spread 18/30 to 22/30 depending on the rule:

| Method | Acc |
|---|---|
| majority | 455/500 |
| mean_confidence_weighted | 455/500 |
| tail_confidence_weighted | 455/500 |
| bottom_window_weighted | 455/500 |
| min_window_weighted | 455/500 |
| top10_tail_filtered | 451/500 |
| top10_bottom_window_filtered | 445/500 |

## Settings

`WINDOW = 256`, `PROBE_EVERY = 512`, `PROBE_MIN_TOKS = 512`. Everything else is
the repo default for this model at the commit this ran from: 16 seats, 32-trace
cap, `BAR_KEEP_TOP` 10 (= PeerConf-**low**), `BAR_MIN_CALIBRATORS` 1, consensus
0.95, 64k-token cap per trace, `GRAD_CONF` 0.95, `GRAD_EWT` on, loop guard on
(cut), temperature 0.6 / top-p 0.95 / top-k off, top-20 logprobs. 2x H200 SXM,
tensor-parallel 2, stock vLLM.

All three changed values were read back out of **all 500 stored pkl configs**,
not assumed from the launch arguments: every file reports
`(WINDOW, PROBE_EVERY, PROBE_MIN_TOKS) = (256, 512, 512)`.

## Tokens and time

| | |
|---|---|
| Total tokens | 24,738,575 (24,000,389 trace + 738,186 probe) |
| Mean / median tokens per question | 49,477 / 17,112 |
| Token spread per question | min 8,103 · p75 44,282 · p90 114,449 · p99 548,973 · max 739,696 |
| Elapsed generation wall clock | 179.2 min (2.99 h) |
| GPU container time | 303.2 container-min across 7 containers |
| Wall clock per question | min 3s · median 8s · p75 23s · p90 60s · p99 404s · max 589s |

Mean token use is nearly three times the median: a small tail of questions
dominates. Q9, Q18 and Q43 are the expensive end and their figures are included
below.

Elapsed wall clock is shorter than container time because part of the sweep ran
as two simultaneous workers on disjoint question ranges, a 1.69x parallelism
factor. Two workers get exactly the same per-container KV cache as one
(114.73 GiB per GPU, 1,670,848 tokens, 25.50x max concurrency at 65,536 tokens
per request), so parallel and sequential chunks are directly comparable.

## Mechanics

Trace termination across all 9,718 traces:

| Reason | Traces | Share |
|---|---|---|
| abandoned (consensus / certificate drain) | 7,153 | 73.6% |
| graduated (commitment probe) | 1,797 | 18.5% |
| cut at the bar | 593 | 6.1% |
| natural finish | 174 | 1.8% |
| truncated | 1 | 0.0% |

Three-quarters of all traces are drained mid-flight when the question closes,
so most generated work is discarded by design rather than run to completion.

**The loop guard fired zero times across the entire run.** On MATH-500's short
traces it costs nothing and catches nothing, unlike the longer AIME/HMMT traces
it was built for.

Probes and graduation: 41,394 probes fired, 22 failed (0.05%, and the same rate
appears in single-worker and parallel chunks alike, so it is not a concurrency
artefact). 41,317 probes (99.8%) carried a parsable answer, of which 30.5% were
already correct at probe time — expected, since most probes fire long before a
trace has converged. The closure (`ewt`) flag was set on 22.3% of probes.
1,797 traces graduated and 85.4% of those had the right answer. Graduation
token positions run min 512 · p25 512 · median 1,025 · p75 3,584 · p90 9,856 ·
max 42,141: the p25 sitting exactly on the `PROBE_MIN_TOKS` floor shows a large
share of traces graduate at the first legally permitted probe.

## Read this before using the numbers

**(a) `PROBE_MIN_TOKS` silently stopped meaning what its comment says.** The
repo default is 2048, and the comment beside it reads "no probes before the
first full window" — true when `WINDOW` was also 2048. At `WINDOW = 256` a full
window is 256 tokens, but the constant would still have blocked every probe
until token 2048, so `PROBE_EVERY = 512` would have governed only the back half
of a trace's life. Nothing in the code couples the two; the gap was caught by
reading the comment against the new value and re-derived explicitly with Mofe,
who set it to 512. This is a concrete instance of the static-hyperparameter
coordination problem in section 5.1: a constant whose correctness depends on
another constant, with no mechanism tying them together and no error when they
disagree.

**(b) Q94 — the bar discarded a correct majority.** The AIME25 Q0/Q12 pattern
from section 5.2 reproduces here, exactly once in 500 questions. 19 traces
finished; the unfiltered majority among them was `80`, which is correct. The
frozen vote bar cut the pool to 3 eligible voters and the filtered result
flipped to `130^\circ`, which is wrong. So one of the 45 misses is caused by
the confidence filter discarding a correct answer the run had already produced,
not by the model failing to find it. A vote bar froze on only 4 of 500
questions at all, and removed at least one finisher on those same 4 — so the
filter is nearly inert on this benchmark, and still managed to cost a question
on one of the four occasions it acted.

**(c) The ballot-count-correlates-with-accuracy pattern is untestable here, not
absent.** 457 of 500 questions were decided on exactly 3 ballots — the
consensus floor — so there is essentially no spread in ballot count to
correlate accuracy against. The distribution is min 2 · median 3 · p99 15 ·
max 19, with the 10-19 ballot tail being the handful of hard questions where
consensus never landed. This is not evidence against the AIME25 finding; the
dataset simply cannot test it.

**(d) The timeline dropped-trace rate is 7.29% here against 41% in the old
w2048 figures, and that is structural rather than luck.** A trace that never
fills one full window has no sliding-window confidence value, so it cannot be
plotted and is omitted (the plotter at this commit at least declares the
omission in its counts, title and legend rather than hiding it). At
WINDOW = 2048 the old MATH-500 run lost 268 of 659 traces this way, because the
median trace was shorter than the window. At WINDOW = 256, 708 of 9,718 traces
are omitted — and the composition matters more than the rate: **590 of those
708 never generated a single token**, being seats that were never filled
because the question closed first, while only **118 are real work the window
failed to cover**. The figures are no longer materially incomplete.

**(e) The 45 wrong answers are not 45 reasoning failures.** The headline figure
is the official one, 455/500 = 91.0%, graded by the run's own scorer, and that
is the number to quote. Separately, classifying the 45 with a normaliser
strictly more permissive than `math_equal` — dropping degree marks, currency
symbols and thousands separators, unwrapping a fixed list of unit words,
expanding `a \pm b` into its two values, and comparing comma-separated lists as
unordered sets — puts **25 of the 45 as notation mismatches** where the value is
right and only the spelling falls outside the grader (`90` against `90^\circ`,
`-2,1` against `1,-2`, `52` against `52_8`, and a gold answer of
`\$36` — a money value inside the word problem itself — against `36`), leaving **20
as genuine reasoning errors** (`Carla` for `Evelyn`, `12` for `6`, `154` for
`116`). 25 is a floor, not a point estimate: several entries still in the
reasoning bucket — Q166, Q257, Q383, Q422, Q467 — look like unit or
set-notation cases the fixed rule set did not catch, and were deliberately left
unadjusted rather than hand-labelled. Read the ceiling as roughly 96%, the
floor as the official 91.0%, and prefer the official figure in any table.

## Data integrity

Every one of the 500 pkls was unpickled and checked: filename QID matches the
stored `qid`, dataset and model match, ground truth matches
`benchmarks/math500.jsonl`, and the config dict carries the expected 25
settings. Cross-contamination was checked across the full corpus at once rather
than chunk by chunk: **500 distinct prompt hashes across 500 questions and
9,080 distinct trace bodies, zero collisions**. Part of the sweep ran as two
simultaneous workers, so this check is what rules out overlap between them in
fact and not merely by construction.

## Files

Raw pkls are not in git. They live on the Modal Volume `peerconf-out` under
`math500/deepseek_w256/peerconf_out/`, alongside the per-worker stdout, vLLM
and event logs under `math500/deepseek_w256/logs/`.

`timelines/` here is a **deliberately chosen 48-figure subset**: all 45
questions the scorer marked wrong, plus Q9, Q18 and Q43, the expensive tail.
All 500 figures are on the same Volume under
`math500/deepseek_w256/peerconf_out/` for anyone who needs the rest.

Green = that trace's own answer is correct, crimson = wrong, both graded with
the run's own scorer so a figure cannot disagree with the table above. Gray + X
= cut at the bar, khaki dashed = truncated, blue dotted = drained when the
question closed. Stars = graduated by a commitment probe; small black dots mark
where each probe fired.

### The expensive tail

#### Q9 — correct, 346,699 tokens
![Q9](timelines/q09_peerconf_confidence_timeline.png)

#### Q18 — correct, 331,894 tokens
![Q18](timelines/q18_peerconf_confidence_timeline.png)

#### Q43 — correct, 221,570 tokens
![Q43](timelines/q43_peerconf_confidence_timeline.png)

### Notation mismatches (value right, spelling outside the grader)

Q7 `90^\circ`, Q25 `1,-2`, Q30 `52_8`, Q96 `1 \pm \sqrt{19}`, Q99, Q100, Q109,
Q156, Q177, Q217, Q233, Q235, Q242, Q255, Q260, Q261, Q267, Q301, Q379, Q393,
Q408, Q420, Q459, Q460, Q488.

![Q7](timelines/q07_peerconf_confidence_timeline.png)
![Q25](timelines/q25_peerconf_confidence_timeline.png)
![Q30](timelines/q30_peerconf_confidence_timeline.png)
![Q96](timelines/q96_peerconf_confidence_timeline.png)
![Q99](timelines/q99_peerconf_confidence_timeline.png)
![Q100](timelines/q100_peerconf_confidence_timeline.png)
![Q109](timelines/q109_peerconf_confidence_timeline.png)
![Q156](timelines/q156_peerconf_confidence_timeline.png)
![Q177](timelines/q177_peerconf_confidence_timeline.png)
![Q217](timelines/q217_peerconf_confidence_timeline.png)
![Q233](timelines/q233_peerconf_confidence_timeline.png)
![Q235](timelines/q235_peerconf_confidence_timeline.png)
![Q242](timelines/q242_peerconf_confidence_timeline.png)
![Q255](timelines/q255_peerconf_confidence_timeline.png)
![Q260](timelines/q260_peerconf_confidence_timeline.png)
![Q261](timelines/q261_peerconf_confidence_timeline.png)
![Q267](timelines/q267_peerconf_confidence_timeline.png)
![Q301](timelines/q301_peerconf_confidence_timeline.png)
![Q379](timelines/q379_peerconf_confidence_timeline.png)
![Q393](timelines/q393_peerconf_confidence_timeline.png)
![Q408](timelines/q408_peerconf_confidence_timeline.png)
![Q420](timelines/q420_peerconf_confidence_timeline.png)
![Q459](timelines/q459_peerconf_confidence_timeline.png)
![Q460](timelines/q460_peerconf_confidence_timeline.png)
![Q488](timelines/q488_peerconf_confidence_timeline.png)

### Reasoning errors

Q4, Q46, **Q94 (the bar pathology, see caveat b)**, Q120, Q138, Q154, Q166,
Q240, Q257, Q264, Q284, Q303, Q317, Q324, Q369, Q383, Q400, Q422, Q467, Q478.

![Q4](timelines/q04_peerconf_confidence_timeline.png)
![Q46](timelines/q46_peerconf_confidence_timeline.png)
![Q94](timelines/q94_peerconf_confidence_timeline.png)
![Q120](timelines/q120_peerconf_confidence_timeline.png)
![Q138](timelines/q138_peerconf_confidence_timeline.png)
![Q154](timelines/q154_peerconf_confidence_timeline.png)
![Q166](timelines/q166_peerconf_confidence_timeline.png)
![Q240](timelines/q240_peerconf_confidence_timeline.png)
![Q257](timelines/q257_peerconf_confidence_timeline.png)
![Q264](timelines/q264_peerconf_confidence_timeline.png)
![Q284](timelines/q284_peerconf_confidence_timeline.png)
![Q303](timelines/q303_peerconf_confidence_timeline.png)
![Q317](timelines/q317_peerconf_confidence_timeline.png)
![Q324](timelines/q324_peerconf_confidence_timeline.png)
![Q369](timelines/q369_peerconf_confidence_timeline.png)
![Q383](timelines/q383_peerconf_confidence_timeline.png)
![Q400](timelines/q400_peerconf_confidence_timeline.png)
![Q422](timelines/q422_peerconf_confidence_timeline.png)
![Q467](timelines/q467_peerconf_confidence_timeline.png)
![Q478](timelines/q478_peerconf_confidence_timeline.png)
