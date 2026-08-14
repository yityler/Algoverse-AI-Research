# PeerConf vs DeepConf — comparative summary

MATH-500, questions Q0–Q24. Both arms ran against the same vLLM server in the same
session on 2x H200, so hardware, model and decoding are identical by construction.
The only difference is the method.

## Headline

| | PeerConf-low | DeepConf-low | difference |
|---|---|---|---|
| **Total tokens** | 1,928,910 | 3,215,459 | **40.0% fewer** |
| **Accuracy** | 25/25 (100%) | 24/25 (96%) | **+1 question** |
| Mean tokens/question | 77,156 | 128,618 | 40% fewer |
| Median tokens/question | 60,823 | 78,552 | 23% fewer |
| Cheapest question | 11,643 | 15,172 | |
| Most expensive question | 353,281 | 472,832 | |
| Questions won on cost | **24/25** | 1/25 | |

**PeerConf spends 40% fewer tokens and answers one more question correctly.**

## How they get there

| | PeerConf | DeepConf |
|---|---|---|
| Traces generated | 595 | 416 |
| Median trace length | 1,948 tokens | 5,148 tokens |
| Finished with an answer | 84 | 402 |
| Cut at the bar | 191 | 14 |
| Drained when race closed | 320 | 0 |
| Tokens on traces that answered | 532,856 (**28%**) | 3,188,339 (**99%**) |
| Ballots per question (min/median/max) | 1 / 3 / 14 | 16 / 16 / 18 |

These two arms are not cheaper and dearer versions of the same behaviour. They are
different strategies.

**DeepConf finishes almost everything it starts.** 402 of 416 traces ran to completion;
only 14 were ever cut. 99% of its tokens went into traces that produced an answer. Its
cost is not waste — it is the warm-up: sixteen traces run to the end on every question
before a single decision is made, at a median 5,148 tokens each.

**PeerConf finishes almost nothing.** Only 84 of 595 traces reached an answer. 191 were
cut at the bar and 320 were drained when the race closed early. Just 28% of its tokens
went into traces that answered. It wins by killing work in progress, not by working more
efficiently.

## The cost of that strategy

PeerConf decides on a median of 3 ballots per question, and on
at least one question it decided on **1**. DeepConf decides on a median of
16.

A correct answer resting on one surviving trace is a materially weaker result than the
same answer with sixteen agreeing, and the accuracy column cannot tell them apart. This
is the main thing the headline number hides, and it is worth reporting per question.

## Where PeerConf lost

**Q8** — PeerConf 28,389 tokens vs DeepConf 23,027 (23% more). Both correct. PeerConf cut 27 traces, kept launching replacements, and decided on 3 ballots; DeepConf decided on 16.

Aggressive culling can cost more than it saves: every cut trace frees a seat, and the
replacement has to be paid for too.

## Caveats

- **n = 25.** Twenty-five questions of MATH-500's five hundred. Directional, not final.

- **Grading.** Figures use `aws/grading.py`. Raw `math_equal` scores the same runs
  PeerConf 23/25 and DeepConf 22/25, rejecting `\dfrac` vs
  `\frac` with spacing, and `90` vs `90^\circ`. Both arms lose the same questions, so
  the comparison holds either way.

- **WINDOW = 256, not the repo default of 2048.** At 2048, 41% of MATH-500
  traces produced no confidence signal and DeepConf crashed outright. This is the only
  setting changed from Mofe's AIME configuration.

- **Single run, temperature 0.6.** Not reproducible token-for-token; a rerun moves the
  numbers. Accuracy on 25 questions moves in 4-point steps.

- **Same direction as AIME25** (22.8% fewer tokens, +1 question there; 40% and +1 here),
  so the result is not an artefact of one benchmark.

