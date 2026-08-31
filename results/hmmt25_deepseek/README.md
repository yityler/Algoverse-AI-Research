# HMMT25 — DeepSeek-R1-0528-Qwen3-8B

peerconf-low and deepconf-low on all 30 questions, matched settings.

The AIME25 runs on the same model and on GPT-OSS-20B are in
[../aime25](../aime25/README.md) and [../aime25_gptoss](../aime25_gptoss/README.md).

## Results

| Method | Model | Dataset | Token | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | DeepSeek-8B | HMMT25 (Q0-29) | 13.30M | 73.3% | 443K |
| DeepConf-low | DeepSeek-8B | HMMT25 (Q0-29) | 17.31M | 76.7% | 577K |

PeerConf spends 23.2% fewer tokens and answers one fewer question.
PeerConf token counts include the tokens its commitment probes generate.
Accuracy is the min-window-weighted vote in both arms; the table below breaks
it out by voting method.

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.
Both arms on 2x H200 SXM, same model, same cap, same tau, WINDOW 2048,
temperature 0.6 / top-p 0.95 / top-k off.

Wall clock, PeerConf 170.7 min against DeepConf 290.1 min over the same 30
questions. The two arms ran sequentially, one question on the box at a time, so
these are per-question costs and compare directly.

Traces actually generated: PeerConf 23.7 per question, DeepConf 22.4.

The 23.2% saving is close to the 24.8% the same two arms recorded on AIME25 with
this model, so the effect reproduces on a second and harder benchmark. The
accuracy ordering does not: on AIME25 the arms tied at 83.3%, here DeepConf is
one question ahead.

## Read this before using the numbers

**The headline gap is one question, but the arms differ on seven.** They agree on
19 questions, both miss 4, and split the remaining 7: PeerConf alone gets Q12,
Q17 and Q29; DeepConf alone gets Q13, Q14, Q24 and Q28. Two methods landing
within a question of each other is not the same as two methods behaving alike,
and a 30-question benchmark cannot separate them on a 22-versus-23 result.

**DeepConf's vote rests on very few traces.** Its 10th-percentile filter admits
only the warmup traces at or above the frozen bar, and across this sweep that
discarded 417 of 477 warmup ballots, 87%. On 18 of 30 questions the voting pool
is exactly 2. The filter is doing real work rather than merely trimming: scored
on the same warmup traces without it, plain majority gets 20/30 against
DeepConf-low's 23/30 (see SC@16 below). But it means the reported answer is
often decided by one or two survivors of sixteen.

**PeerConf is not uniformly cheaper.** It spends fewer tokens on 23 of 30
questions, not all of them. Q2, Q12, Q15, Q16, Q17, Q19 and Q28 cost it more
than DeepConf, and on Q2 it spends 21.3% more.

## Per question

| Q | GT | PeerConf | DeepConf | PeerConf tokens | DeepConf tokens | Saving |
|---|---|---|---|---|---|---|
| 0 | `103` | yes | yes | 65,765 | 139,366 | 52.8% |
| 1 | `3375` | yes | yes | 65,752 | 158,434 | 58.5% |
| 2 | `\frac{1}{576}` | yes | yes | 532,388 | 438,984 | -21.3% |
| 3 | `-984` | yes | yes | 132,237 | 302,445 | 56.3% |
| 4 | `890` | yes | yes | 131,323 | 313,557 | 58.1% |
| 5 | `\frac{1311}{2017}` | yes | yes | 502,353 | 586,835 | 14.4% |
| 6 | `\frac{9 \sqrt{23}}{23}` | yes | yes | 241,597 | 433,841 | 44.3% |
| 7 | `1-\frac{2}{\pi}` | yes | yes | 225,099 | 485,743 | 53.7% |
| 8 | `1037` | yes | yes | 429,432 | 445,162 | 3.5% |
| 9 | `\frac{-1+\sqrt{17}}{2}, \frac{-1-\sqrt{17}}{2}` | yes | yes | 500,512 | 1,062,998 | 52.9% |
| 10 | `56` | yes | yes | 264,218 | 457,930 | 42.3% |
| 11 | `29` | yes | yes | 329,827 | 657,363 | 49.8% |
| 12 | `105` | yes | no (`33`) | 945,110 | 852,418 | -10.9% |
| 13 | `2304` | no (`2592`) | yes | 927,999 | 993,057 | 6.6% |
| 14 | `200` | no (`202`) | yes | 560,272 | 859,775 | 34.8% |
| 15 | `6300` | yes | yes | 473,719 | 440,883 | -7.4% |
| 16 | `2^{25} \cdot 26!` | no (`4 \times 26!`) | no (`4 \times 26!`) | 655,936 | 580,512 | -13.0% |
| 17 | `\frac{2025}{101}` | yes | no (`\dfrac{675}{67}`) | 1,084,213 | 961,052 | -12.8% |
| 18 | `\frac{4}{9}` | no (`\dfrac{1}{2}`) | no (`\dfrac{1}{2}`) | 731,494 | 984,474 | 25.7% |
| 19 | `\frac{448}{3}` | no (`15`) | no (`28`) | 750,589 | 686,319 | -9.4% |
| 20 | `26` | yes | yes | 66,024 | 187,159 | 64.7% |
| 21 | `63` | yes | yes | 131,576 | 397,031 | 66.9% |
| 22 | `8\sqrt{10}` | yes | yes | 180,852 | 220,211 | 17.9% |
| 23 | `20` | no (`100`) | no (`100`) | 263,412 | 685,015 | 61.5% |
| 24 | `\sqrt{23}-2 \sqrt{3}` | no (`3`) | yes | 526,031 | 1,167,233 | 54.9% |
| 25 | `9\sqrt{15}` | yes | yes | 197,429 | 305,787 | 35.4% |
| 26 | `\frac{7}{18}` | yes | yes | 197,917 | 315,067 | 37.2% |
| 27 | `\sqrt{6}` | yes | yes | 198,182 | 321,076 | 38.3% |
| 28 | `14+4\sqrt{37}` | no (`\dfrac{154}{5}`) | yes | 988,271 | 846,958 | -16.7% |
| 29 | `\sqrt{\frac{95}{24}}` | yes | no (`5`) | 1,001,857 | 1,027,949 | 2.5% |
| **overall** | | **22/30** | **23/30** | **13,301,386** | **17,314,634** | **23.2%** |

Saving is PeerConf against DeepConf on that question; a negative number means
PeerConf spent more. The answer columns are the min-window-weighted vote, as
everywhere else on this page.

## Accuracy by voting method

| Method | PeerConf | DeepConf |
|---|---|---|
| majority | 20/30 | 22/30 |
| mean_confidence_weighted | 20/30 | 23/30 |
| tail_confidence_weighted | 22/30 | 23/30 |
| bottom_window_weighted | 21/30 | 23/30 |
| min_window_weighted | 22/30 | 23/30 |
| top10_tail_filtered | 18/30 | 22/30 |
| top10_bottom_window_filtered | 20/30 | 22/30 |

The two arms rank differently under different rules, which is the reason the
voting rule has to be stated with any number taken from this page. PeerConf's
spread is 18/30 to 22/30 depending on the rule; DeepConf's is 22/30 to 23/30.

## SC@16, computed from DeepConf's own warmup traces

DeepConf's warmup phase runs 16 traces that are, in its own words, "run fully,
never judged": the judge and kill paths are gated on the online phase, and
consensus is only evaluated once the warmup has fully drained. Those 16 traces
per question are therefore already an unmanaged self-consistency sample, and a
majority vote over them costs nothing extra to compute.

| Method | Acc | Total tokens | Mean token/Q |
|---|---|---|---|
| SC@16 (plain majority) | 20/30 (66.7%) | 14,387,189 | 479K |

**This is not an independent SC sample.** It re-votes the traces DeepConf
already generated, so it shares that run's sampling stream and is a strict
subset of DeepConf's own 17.31M tokens. It answers "what would these traces say
without the confidence filter", not "what would a separate SC run say".

The grading was validated rather than assumed: replicating DeepConf's own
bar-filtered ballot pool reproduces its reported majority on all 18 questions
where the online wave never ran, which is where the two must agree by
construction. The unfiltered SC@16 vote then differs from DeepConf on exactly
the questions the filter changes.

The 30 raw DeepConf-low pkls these numbers come from are committed under
[`deepconf_pkls/`](deepconf_pkls/README.md), with the per-path answer and token
count for all 16 warmup traces on every question. Raw pkls are otherwise kept
off git in this repo; that directory is a deliberate exception, made so the
warmup paths can be combined with a separate SC@32 run into a plain majority
vote over all 32 paths per question.

## SC@32 pilot — 5 of 30 questions, evidence only

A native SC@32 arm (`sc/cell2_sc.py`, new in this run) was piloted on five
questions and then stopped. **These are not a headline row and no SC@32 accuracy
figure should be quoted from them.**

| Q | GT | SC@32 majority | tokens | traces |
|---|---|---|---|---|
| 0 | `103` | yes | 259,558 | 32 |
| 1 | `3375` | yes | 325,549 | 32 |
| 2 | `\frac{1}{576}` | no (`576`) | 986,231 | 32 |
| 3 | `-984` | yes | 678,052 | 32 |
| 24 | `\sqrt{23}-2 \sqrt{3}` | yes | 1,486,490 | 32 |

Q0 and Q24 were chosen as the cheapest and the most expensive question by
DeepConf's measured profile; Q1, Q2 and Q3 followed in order before the run was
stopped.

**Consistency check.** SC@32 and SC@16 independently return the same wrong
answer on Q2: both pick `576` where the gold is `\frac{1}{576}`, and both
managed arms get it right. Two separately-computed self-consistency votes
agreeing on the same failure, against two managed arms that agree on the
correct answer, is what a real filter effect looks like rather than noise.

**The draws are genuinely independent.** vLLM on this stack returns the same
completions for the same prompt at the same batch width, so an unseeded SC@32
run as two waves of 16 would have drawn the same 16 answers twice and reported
them as 32 votes. Each trace is given a distinct seed and the runner prints a
distinctness diagnostic; it read 32/32 on every piloted question.

**Dropping the logprobs payload is a harness optimisation, not a methodological
difference.** SC reads only the final boxed answer, so the per-token top-20
logprobs the other two arms stream to feed their confidence window are pure
transport overhead here. Removing them roughly doubled throughput, 1,920 tok/s
against DeepConf's 995 on the same question. Sampling parameters and token
counts are untouched: the same temperature, top-p and top-k, and the same number
of tokens generated. Only the size of the JSON coming back over the wire changes.

## Caveats

**AIME25's published DeepSeek row mixes two implementations.** 26 of its 30
questions were run on an earlier bar/voting implementation and Q9, Q12, Q13 and
Q27 were rerun after an extractor fix. The HMMT25 numbers on this page come from
a third, current implementation, run end to end in one pass. AIME25 and HMMT25
DeepSeek rows are therefore not strictly like-for-like, and the 24.8%-versus-23.2%
comparison above should be read as two close measurements rather than one
controlled difference.

**This repo had no prior native SC@n implementation.** `sc/cell2_sc.py` is the
first, added in this run. The SC@32 rows for MATH500 and AIME25 in Table 1 were
produced externally and are a different implementation from this one; nothing on
this page should be compared against them without checking that first.

**The model is DeepSeek-R1-0528-Qwen3-8B**, which is what "DeepSeek-8B" refers to
throughout this repo. It is not DeepSeek-R1-Distill-Llama-8B, which belongs to a
different family.

**Pending follow-up, not blocking.** The PeerConf-low and DeepConf-low headline
numbers here use the min-window-weighted vote; SC uses plain majority, which is
the only rule available to it since it keeps no confidence signal. A three-way
comparison across those two rules would not be a like-for-like reading.
`three_way_table` is written and needs to be run, with its output added in a
follow-up commit, before any three-way table is presented as final.

## Run cost

Roughly 480 GPU-min across the sweep and its resumes on 2x H200 SXM, about $75.
The run is resumable per question, so the two budget interruptions cost only the
in-flight question each time. The SC@32 pilot is a further $9.70 and is tracked
separately.

Raw pkls are not in git. They live on the Modal Volume `peerconf-out` under
`peerconf_out/`, `deepconf_out/` and `sc_out/`.

## Confidence timelines

Drawn by the repo's own `cell3_confidence_timeline.py` and
`cell3_deepconf_timeline.py`, which grade with the same `tidy_tex` + `math_equal`
the runs voted with.

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
