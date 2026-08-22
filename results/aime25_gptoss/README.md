# AIME25 — GPT-OSS-20B

peerconf-low and deepconf-low on all 30 questions, matched settings.

The DeepSeek-8B run on the same benchmark is in [../aime25](../aime25/README.md).

## Results

| Method | Model | Dataset | Token | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | GPT-OSS-20B | AIME25 (Q0-29) | 9.84M | 86.7% | 328K |
| DeepConf-low | GPT-OSS-20B | AIME25 (Q0-29) | 18.26M | 83.3% | 609K |

PeerConf spends 46.1% fewer tokens and answers one more question.
PeerConf token counts include the tokens its commitment probes generate.
Accuracy is the min-window-weighted vote in both arms; the table below breaks
it out by voting method.

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.
Both arms on 2x H200 SXM, same model, same cap, same tau, reasoning_effort high.

Wall clock, PeerConf 104.3 min against DeepConf 187.8 min over the same 30
questions. The two arms ran sequentially, one question on the box at a time, so
these are per-question costs and compare directly. A concurrent schedule would
have measured contention between whatever happened to be co-resident instead.

Average length of a path:

PeerConf - 15,338 tokens (including probe tokens)

DeepConf - 30,032 tokens

Average length of a path that finished with an answer:

PeerConf - 14,307 (including probe tokens)

DeepConf - 25,825

Traces actually generated: PeerConf 21.4 per question, DeepConf 20.3.

## Read this before using the numbers

**Every PeerConf ballot on the hard tier came from a commitment probe.** Across
the ten hard questions (problems 11-15 of each paper) PeerConf recorded zero
natural finishers: all 42 of its hard-tier graduations were the only source of a
ballot there. Its only natural finishers anywhere in the run are on Q0, Q2, Q15
and Q16, whose traces run about 2k tokens and end before the probe schedule can
fire.

**That is the probe pre-empting traces, not the model failing to finish.** It
would be easy to read the line above as "these questions do not fit in 64k", and
for most of them that is false. DeepConf has no probe, and on the same ten hard
questions it finished 12 to 16 traces naturally on Q10, Q11, Q25, Q26 and Q28.
Their unmanaged control traces run 24k-53k tokens and box an answer. So a
counterfactual PeerConf with the probe switched off would not return nothing on
the hard tier; it would spend far more tokens and finish some of them.

**Six questions genuinely do not fit in 64k, and they are the ones that hurt.**
Q12, Q13, Q14, Q19, Q27 and Q29 have control traces that hit the cap without
boxing anything. That set, not the hard tier as a whole, is where the probe is
load-bearing, and it is where DeepConf's structural limit shows.

**DeepConf returns nothing on four questions.** Q13, Q14, Q27 and Q29 end with
an empty voting pool, not a wrong answer. Its 16 warmup traces cannot close
early, so on a question whose natural length exceeds the cap the arm spends its
whole budget and has nothing to vote on. All four are in the capped six.
PeerConf answered all four and was right on one, because a probe can read an
answer out of a path that never finished.

**One DeepConf question is graded wrong that the model got right.** Q0's gold is
`70` and the winning trace wrote `\boxed{21+49=70}`. Extraction is not at fault:
`extract_answer` pulled the brace contents correctly. The gap is in matching.
`tidy_tex` is cosmetic only and never reduces `a+b=c` to `c`, and `math_equal`
parses expressions rather than equations, so `math_equal("21+49=70", "70")` is
false. Counted right, DeepConf's majority vote is 25/30 rather than 24/30. The
min-window-weighted vote already scores it right, which is why the headline
table is unaffected. The numbers here are left as the run graded them; the gap
is named rather than patched over.

## Per question

| Q | GT | PeerConf | DeepConf | PeerConf tokens | DeepConf tokens | Saving |
|---|---|---|---|---|---|---|
| 0 | 70 | yes | yes | 33,088 | 101,102 | 67.3% |
| 1 | 588 | yes | yes | 131,851 | 681,757 | 80.7% |
| 2 | 16 | yes | yes | 48,527 | 69,929 | 30.6% |
| 3 | 117 | yes | yes | 66,289 | 193,443 | 65.7% |
| 4 | 279 | yes | yes | 131,611 | 325,602 | 59.6% |
| 5 | 504 | yes | yes | 65,698 | 122,813 | 46.5% |
| 6 | 821 | no (`271`) | yes | 131,830 | 700,217 | 81.2% |
| 7 | 77 | yes | yes | 65,938 | 318,481 | 79.3% |
| 8 | 62 | yes | yes | 396,211 | 768,077 | 48.4% |
| 9 | 81 | yes | yes | 501,041 | 739,322 | 32.2% |
| 10 | 259 | yes | yes | 323,345 | 837,694 | 61.4% |
| 11 | 510 | yes | yes | 197,219 | 708,106 | 72.1% |
| 12 | 204 | yes | no (`\dfrac{637}{3}`) | 593,501 | 993,215 | 40.2% |
| 13 | 60 | no (`238`) | no (no answer) | 1,249,405 | 1,158,449 | -7.9% |
| 14 | 735 | no (`683`) | no (no answer) | 1,053,721 | 1,352,305 | 22.1% |
| 15 | 468 | yes | yes | 56,154 | 85,113 | 34.0% |
| 16 | 49 | yes | yes | 56,272 | 83,149 | 32.3% |
| 17 | 82 | yes | yes | 125,274 | 827,971 | 84.9% |
| 18 | 106 | yes | yes | 119,301 | 312,965 | 61.9% |
| 19 | 336 | yes | yes | 718,963 | 1,258,713 | 42.9% |
| 20 | 293 | yes | yes | 66,045 | 218,222 | 69.7% |
| 21 | 237 | yes | yes | 65,719 | 217,205 | 69.7% |
| 22 | 610 | yes | yes | 327,937 | 786,886 | 58.3% |
| 23 | 149 | yes | yes | 198,523 | 582,854 | 65.9% |
| 24 | 907 | yes | yes | 65,722 | 520,930 | 87.4% |
| 25 | 113 | yes | yes | 132,014 | 505,867 | 73.9% |
| 26 | 19 | yes | yes | 194,345 | 396,971 | 51.0% |
| 27 | 248 | yes | no (no answer) | 1,197,557 | 1,517,762 | 21.1% |
| 28 | 104 | yes | yes | 263,155 | 573,792 | 54.1% |
| 29 | 240 | no (`188`) | no (no answer) | 1,265,673 | 1,300,799 | 2.7% |
| **overall** | | **26/30** | **25/30** | **9,841,929** | **18,259,711** | **46.1%** |

Saving is PeerConf against DeepConf on that question; a negative number means
PeerConf spent more. PeerConf is cheaper on 29 of the 30.

## Accuracy by voting method

| Method | PeerConf | DeepConf | DeepConf, Q0 counted right |
|---|---|---|---|
| majority | 26/30 | 24/30 | 25/30 |
| mean_confidence_weighted | 26/30 | 25/30 | 25/30 |
| tail_confidence_weighted | 26/30 | 25/30 | 25/30 |
| bottom_window_weighted | 26/30 | 25/30 | 25/30 |
| min_window_weighted | 26/30 | 25/30 | 25/30 |
| top10_tail_filtered | 25/30 | 24/30 | 24/30 |
| top10_bottom_window_filtered | 26/30 | 24/30 | 25/30 |

## The hard tier

The ten hard questions, with where PeerConf's ballots came from. The answer
column is the min-window-weighted vote, as everywhere else on this page.

| Q | GT | PeerConf | natural finishers | graduated | graduated correct | ballots |
|---|---|---|---|---|---|---|
| 10 | 259 | yes | 0 | 3 | 3/3 | 3 |
| 11 | 510 | yes | 0 | 3 | 3/3 | 3 |
| 12 | 204 | yes | 0 | 3 | 3/3 | 3 |
| 13 | 60 | no (`238`) | 0 | 2 | 0/2 | 2 |
| 14 | 735 | no (`683`) | 0 | 1 | 0/1 | 1 |
| 25 | 113 | yes | 0 | 3 | 3/3 | 3 |
| 26 | 19 | yes | 0 | 15 | 14/15 | 15 |
| 27 | 248 | yes | 0 | 6 | 4/6 | 6 |
| 28 | 104 | yes | 0 | 3 | 3/3 | 3 |
| 29 | 240 | no (`188`) | 0 | 3 | 1/3 | 3 |

The natural-finisher column is zero the whole way down, but that is a fact about
PeerConf's own schedule rather than about the questions. A graduation ends the
path that earned it, so a trace that would have finished on its own is recorded
as graduated instead, and consensus kills the rest. The last column of the
previous section is the check: on Q10, Q11, Q25, Q26 and Q28 the DeepConf arm,
which has no probe, finished most of its traces naturally.

Where the questions really do run past the cap is Q12, Q13, Q14, Q27 and Q29 of
this table, whose control traces hit 64k without boxing. Two of the three
PeerConf misses, Q13 and Q14, sit there. Q29 does too.

Q14 was singled out in the earlier smoke test as a case where the probe
graduated a trace onto a wrong answer and consensus followed it. That reading
holds, but it is not special. Wrong graduations appear on questions PeerConf
answers correctly too: Q26 graduated one path onto `734` and still finished
14/15 correct, Q27 graduated two wrong out of six. Across all 30 questions 132
paths graduated and 22 carried a wrong answer, 17%.

What separates the three misses is how many ballots were cast, not the
graduation rate. The seven hard questions PeerConf gets right cast 3, 3, 3, 3,
3, 6 and 15 ballots. The three it loses cast 2, 1 and 3. Q14 decided the
question on one ballot, where a 17% per-graduation error rate is simply the
question's error rate.

## The vote filter, twice

Two DeepConf questions turn on the same thing, and they are worth keeping apart
because only one of them is a grading artefact.

**Q0.** 19 of 20 finishers answered `70`. The frozen bar at 9.3623 admitted two
of them, one carrying `70` and one carrying `21+49=70`, and since the two
strings do not match they landed in different piles. A 19-to-1 agreement became
a 1-1 tie. Unweighted majority broke it toward the malformed ballot; every
min-conf-weighted method broke it toward `70`.

**Q12.** Same filter, no grading component. Four of the eight answering
finishers reached `204`. The bar admitted one ballot, and that ballot carried
`\dfrac{637}{3}`. With a single ballot in the pool every voting method returns
it, so Q12 is wrong in all seven columns and no correction applies.

The shared shape is that DeepConf-low's 10th-percentile filter can discard a
large correct majority and settle the question on one or two survivors. That is
a property of the aggregation rule, not of the reasoning: the paths found the
answer and were filtered out of the vote.

## Not done here

**A minimum-ballot floor was not tried.** The ballot-count pattern above is an
observation on 30 questions, not a result. It suggests refusing to call a
question on graduation-only consensus below some number of ballots, but nothing
was measured and no method code was changed in this run.

**The concurrent-versus-sequential check was not run.** It cannot be run as
specified. Temperature is 1.0, neither cell2 sets a seed, and vLLM's continuous
batching makes sampling depend on batch composition, so two sequential runs of
the same question do not match either. A mismatch would have shown nothing.
Both arms were run sequentially instead, which is why the wall clock above is
usable.

**There is no full-completion reference.** That would need a genuinely unmanaged
full run per question, not the single unmanaged control trace this run carries.
It is left as a gap rather than approximated from the control traces, which
would produce a number not comparable with the one in Tables 2/3.

## Run cost

211 GPU-min on the resumed invocation plus roughly 106 min on a first attempt
that a workspace budget cap killed partway through PeerConf Q29, so about 317
GPU-min, near $48 on 2x H200 SXM. The run is resumable per question, so the cap
cost the in-flight question and nothing else.

The 30 unmanaged control traces are 8.2 min of that, about $1.25, and are
reported here rather than folded into either arm. They are the only uncensored
read on natural trace length in the run, and they are what identifies the six
questions whose reasoning does not fit in 64k.

## Confidence timelines

### Q0
![Q0 peerconf](timelines/q00_peerconf_confidence_timeline.png)
![Q0 deepconf](timelines/q00_deepconf_confidence_timeline.png)

### Q1
![Q1 peerconf](timelines/q01_peerconf_confidence_timeline.png)
![Q1 deepconf](timelines/q01_deepconf_confidence_timeline.png)

### Q2
![Q2 peerconf](timelines/q02_peerconf_confidence_timeline.png)
![Q2 deepconf](timelines/q02_deepconf_confidence_timeline.png)

### Q3
![Q3 peerconf](timelines/q03_peerconf_confidence_timeline.png)
![Q3 deepconf](timelines/q03_deepconf_confidence_timeline.png)

### Q4
![Q4 peerconf](timelines/q04_peerconf_confidence_timeline.png)
![Q4 deepconf](timelines/q04_deepconf_confidence_timeline.png)

### Q5
![Q5 peerconf](timelines/q05_peerconf_confidence_timeline.png)
![Q5 deepconf](timelines/q05_deepconf_confidence_timeline.png)

### Q6
![Q6 peerconf](timelines/q06_peerconf_confidence_timeline.png)
![Q6 deepconf](timelines/q06_deepconf_confidence_timeline.png)

### Q7
![Q7 peerconf](timelines/q07_peerconf_confidence_timeline.png)
![Q7 deepconf](timelines/q07_deepconf_confidence_timeline.png)

### Q8
![Q8 peerconf](timelines/q08_peerconf_confidence_timeline.png)
![Q8 deepconf](timelines/q08_deepconf_confidence_timeline.png)

### Q9
![Q9 peerconf](timelines/q09_peerconf_confidence_timeline.png)
![Q9 deepconf](timelines/q09_deepconf_confidence_timeline.png)

### Q10
![Q10 peerconf](timelines/q10_peerconf_confidence_timeline.png)
![Q10 deepconf](timelines/q10_deepconf_confidence_timeline.png)

### Q11
![Q11 peerconf](timelines/q11_peerconf_confidence_timeline.png)
![Q11 deepconf](timelines/q11_deepconf_confidence_timeline.png)

### Q12
![Q12 peerconf](timelines/q12_peerconf_confidence_timeline.png)
![Q12 deepconf](timelines/q12_deepconf_confidence_timeline.png)

### Q13
![Q13 peerconf](timelines/q13_peerconf_confidence_timeline.png)
![Q13 deepconf](timelines/q13_deepconf_confidence_timeline.png)

### Q14
![Q14 peerconf](timelines/q14_peerconf_confidence_timeline.png)
![Q14 deepconf](timelines/q14_deepconf_confidence_timeline.png)

### Q15
![Q15 peerconf](timelines/q15_peerconf_confidence_timeline.png)
![Q15 deepconf](timelines/q15_deepconf_confidence_timeline.png)

### Q16
![Q16 peerconf](timelines/q16_peerconf_confidence_timeline.png)
![Q16 deepconf](timelines/q16_deepconf_confidence_timeline.png)

### Q17
![Q17 peerconf](timelines/q17_peerconf_confidence_timeline.png)
![Q17 deepconf](timelines/q17_deepconf_confidence_timeline.png)

### Q18
![Q18 peerconf](timelines/q18_peerconf_confidence_timeline.png)
![Q18 deepconf](timelines/q18_deepconf_confidence_timeline.png)

### Q19
![Q19 peerconf](timelines/q19_peerconf_confidence_timeline.png)
![Q19 deepconf](timelines/q19_deepconf_confidence_timeline.png)

### Q20
![Q20 peerconf](timelines/q20_peerconf_confidence_timeline.png)
![Q20 deepconf](timelines/q20_deepconf_confidence_timeline.png)

### Q21
![Q21 peerconf](timelines/q21_peerconf_confidence_timeline.png)
![Q21 deepconf](timelines/q21_deepconf_confidence_timeline.png)

### Q22
![Q22 peerconf](timelines/q22_peerconf_confidence_timeline.png)
![Q22 deepconf](timelines/q22_deepconf_confidence_timeline.png)

### Q23
![Q23 peerconf](timelines/q23_peerconf_confidence_timeline.png)
![Q23 deepconf](timelines/q23_deepconf_confidence_timeline.png)

### Q24
![Q24 peerconf](timelines/q24_peerconf_confidence_timeline.png)
![Q24 deepconf](timelines/q24_deepconf_confidence_timeline.png)

### Q25
![Q25 peerconf](timelines/q25_peerconf_confidence_timeline.png)
![Q25 deepconf](timelines/q25_deepconf_confidence_timeline.png)

### Q26
![Q26 peerconf](timelines/q26_peerconf_confidence_timeline.png)
![Q26 deepconf](timelines/q26_deepconf_confidence_timeline.png)

### Q27
![Q27 peerconf](timelines/q27_peerconf_confidence_timeline.png)
![Q27 deepconf](timelines/q27_deepconf_confidence_timeline.png)

### Q28
![Q28 peerconf](timelines/q28_peerconf_confidence_timeline.png)
![Q28 deepconf](timelines/q28_deepconf_confidence_timeline.png)

### Q29
![Q29 peerconf](timelines/q29_peerconf_confidence_timeline.png)
![Q29 deepconf](timelines/q29_deepconf_confidence_timeline.png)

