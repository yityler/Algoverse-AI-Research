# AIME25

peerconf-low and deepconf-low on all 30 questions, matched settings.

## Results

| Method | Model | Dataset | Token | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | DeepSeek-8B | AIME25 (Q0-29) | 10.06M | 83.3% | 335K |
| DeepConf-low | DeepSeek-8B | AIME25 (Q0-29) | 13.38M | 83.3% | 446K |

PeerConf spends 24.8% fewer tokens at the same accuracy.
PeerConf token counts include the tokens its commitment probes generate.
Accuracy is the min-window-weighted vote in both arms; the table below breaks
it out by voting method.

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.
Both arms on 2x H200 SXM, same model, same cap, same tau.

Average length of a path:

PeerConf - 16,458 tokens (including probe tokens)

DeepConf - 25,346 tokens

Average length of a path that finished with an answer:

w/ graduation - 16,668 (including probe tokens)

w/o graduation - 27,763 (including probe tokens)


## Per question

| Q | GT | PeerConf | DeepConf | PeerConf tokens | DeepConf tokens | Saving |
|---|---|---|---|---|---|---|
| 0 | 70 | yes | yes | 65,701 | 134,219 | 51.0% |
| 1 | 588 | yes | yes | 131,982 | 270,972 | 51.3% |
| 2 | 16 | yes | yes | 66,155 | 217,393 | 69.6% |
| 3 | 117 | yes | yes | 66,186 | 267,945 | 75.3% |
| 4 | 279 | yes | yes | 132,026 | 278,220 | 52.5% |
| 5 | 504 | yes | yes | 65,816 | 127,427 | 48.4% |
| 6 | 821 | yes | yes | 491,089 | 403,087 | -21.8% |
| 7 | 77 | yes | yes | 65,753 | 264,284 | 75.1% |
| 8 | 62 | yes | yes | 197,347 | 626,990 | 68.5% |
| 9 | 81 | yes | yes | 397,161 | 631,868 | 37.1% |
| 10 | 259 | yes | yes | 395,890 | 625,232 | 36.7% |
| 11 | 510 | yes | yes | 329,661 | 566,452 | 41.8% |
| 12 | 204 | no (`\dfrac{487}{3}`) | no (`\dfrac{487}{3}`) | 925,584 | 855,213 | -8.2% |
| 13 | 60 | no (`71`) | no (`62`) | 1,029,879 | 914,889 | -12.6% |
| 14 | 735 | no (`147`) | no (`969`) | 981,134 | 1,026,611 | 4.4% |
| 15 | 468 | yes | yes | 65,764 | 101,064 | 34.9% |
| 16 | 49 | yes | yes | 65,763 | 133,441 | 50.7% |
| 17 | 82 | yes | yes | 197,704 | 334,852 | 41.0% |
| 18 | 106 | yes | yes | 131,589 | 261,538 | 49.7% |
| 19 | 336 | yes | yes | 593,156 | 499,008 | -18.9% |
| 20 | 293 | yes | yes | 131,581 | 272,913 | 51.8% |
| 21 | 237 | yes | yes | 324,269 | 262,437 | -23.6% |
| 22 | 610 | yes | yes | 508,958 | 598,569 | 15.0% |
| 23 | 149 | yes | yes | 197,891 | 495,414 | 60.1% |
| 24 | 907 | yes | yes | 264,303 | 398,336 | 33.6% |
| 25 | 113 | yes | yes | 263,141 | 389,264 | 32.4% |
| 26 | 19 | yes | yes | 264,011 | 381,898 | 30.9% |
| 27 | 248 | no (`208`) | no (`208`) | 1,006,837 | 869,331 | -15.8% |
| 28 | 104 | yes | yes | 197,950 | 461,639 | 57.1% |
| 29 | 240 | no (`188`) | no (`188`) | 503,917 | 712,347 | 29.3% |
| **overall** | | **25/30** | **25/30** | **10,058,198** | **13,382,853** | **24.8%** |

Saving is PeerConf against DeepConf on that question; a negative number means
PeerConf spent more. PeerConf is cheaper on 24 of the 30.

Traces actually generated: PeerConf 21.9 per question, DeepConf 17.6.
DeepConf closes on its warmup wave alone on 27 of the 30 questions, because
the traces clearing its frozen bar agree and the run stops before the online
wave launches.

## Accuracy by voting method

| Method | PeerConf | DeepConf |
|---|---|---|
| majority | 25/30 | 25/30 |
| mean_confidence_weighted | 25/30 | 25/30 |
| tail_confidence_weighted | 25/30 | 25/30 |
| bottom_window_weighted | 25/30 | 25/30 |
| min_window_weighted | 25/30 | 25/30 |
| top10_tail_filtered | 24/30 | 25/30 |
| top10_bottom_window_filtered | 22/30 | 25/30 |

## Graduation threshold

Every path that graduated on a commitment probe, scored against the ground truth,
as GRAD_CONF varies. The end-of-thinking marker stays on throughout. The last two
columns split the paths that graduate at 0.95 but not at this threshold, by
whether the answer they were carrying was right or wrong.

### All questions

| GRAD_CONF | graduations | correct | accuracy | lost wrong | lost correct |
|---|---|---|---|---|---|
| 0.90 | 110 | 87 | 79.1% | 0 | 0 |
| 0.91 | 110 | 87 | 79.1% | 0 | 0 |
| 0.92 | 110 | 87 | 79.1% | 0 | 0 |
| 0.93 | 110 | 87 | 79.1% | 0 | 0 |
| 0.94 | 110 | 87 | 79.1% | 0 | 0 |
| 0.95 | 110 | 87 | 79.1% | 0 | 0 |
| 0.96 | 109 | 87 | 79.8% | 1 | 0 |
| 0.97 | 108 | 87 | 80.6% | 2 | 0 |
| 0.98 | 108 | 87 | 80.6% | 2 | 0 |
| 0.99 | 104 | 84 | 80.8% | 3 | 3 |
| 0.995 | 101 | 84 | 83.2% | 6 | 3 |

### Winnable questions

Q13, Q14, Q27 and Q29 are dropped here. On those four not a single path ever
reached the right answer, in a final answer or in any probe, so no threshold
can rescue them.

| GRAD_CONF | graduations | correct | accuracy | lost wrong | lost correct |
|---|---|---|---|---|---|
| 0.90 | 103 | 87 | 84.5% | 0 | 0 |
| 0.91 | 103 | 87 | 84.5% | 0 | 0 |
| 0.92 | 103 | 87 | 84.5% | 0 | 0 |
| 0.93 | 103 | 87 | 84.5% | 0 | 0 |
| 0.94 | 103 | 87 | 84.5% | 0 | 0 |
| 0.95 | 103 | 87 | 84.5% | 0 | 0 |
| 0.96 | 103 | 87 | 84.5% | 0 | 0 |
| 0.97 | 102 | 87 | 85.3% | 1 | 0 |
| 0.98 | 102 | 87 | 85.3% | 1 | 0 |
| 0.99 | 98 | 84 | 85.7% | 2 | 3 |
| 0.995 | 96 | 84 | 87.5% | 4 | 3 |

Raising the threshold never gains a correct graduation. It can only take paths
away. Up to 0.98 the ones it takes are all wrong, which is why the correct column
stays at 87. From 0.99 it starts taking correct ones too, and by 0.995 it has
thrown away 3 correct graduations to remove 6 wrong ones. The accuracy percentage
still rises, but only because it dropped more wrong than correct, not because
anything improved. The final answer stays 25/30 at every threshold, since those
wrong graduations were already being outvoted.

The two paragraphs below predate the q9/q12 rerun.

The end-of-thinking marker does far more work than the threshold. At GRAD_CONF
0.95, a probe that reached `</think>` is right 85.3% of the time; one that did not
is right 43.5%. Turning the marker off and raising the threshold instead never
catches up, reaching only 80.4% even at 0.999.

A probe is either sure or wrong, with very little in between. Below 0.90, only 14
of 1,879 probes had the right answer, about 0.7%. Below 0.50, none of 1,433 did.
So when a trace is interrupted and the model is not confident, it is not close to
the answer either, it is guessing.

## Confidence timelines

Two figures per question, PeerConf then DeepConf. Each line is a trace's
sliding-window confidence over its own life, coloured by how it ended.

### Q0  ground truth 70

PeerConf: correct, 66K tokens

![Q0 peerconf](timelines/q00_peerconf_confidence_timeline.png)

DeepConf: correct, 134K tokens

![Q0 deepconf](timelines/q00_deepconf_confidence_timeline.png)

### Q1  ground truth 588

PeerConf: correct, 132K tokens

![Q1 peerconf](timelines/q01_peerconf_confidence_timeline.png)

DeepConf: correct, 271K tokens

![Q1 deepconf](timelines/q01_deepconf_confidence_timeline.png)

### Q2  ground truth 16

PeerConf: correct, 66K tokens

![Q2 peerconf](timelines/q02_peerconf_confidence_timeline.png)

DeepConf: correct, 217K tokens

![Q2 deepconf](timelines/q02_deepconf_confidence_timeline.png)

### Q3  ground truth 117

PeerConf: correct, 66K tokens

![Q3 peerconf](timelines/q03_peerconf_confidence_timeline.png)

DeepConf: correct, 268K tokens

![Q3 deepconf](timelines/q03_deepconf_confidence_timeline.png)

### Q4  ground truth 279

PeerConf: correct, 132K tokens

![Q4 peerconf](timelines/q04_peerconf_confidence_timeline.png)

DeepConf: correct, 278K tokens

![Q4 deepconf](timelines/q04_deepconf_confidence_timeline.png)

### Q5  ground truth 504

PeerConf: correct, 66K tokens

![Q5 peerconf](timelines/q05_peerconf_confidence_timeline.png)

DeepConf: correct, 127K tokens

![Q5 deepconf](timelines/q05_deepconf_confidence_timeline.png)

### Q6  ground truth 821

PeerConf: correct, 491K tokens

![Q6 peerconf](timelines/q06_peerconf_confidence_timeline.png)

DeepConf: correct, 403K tokens

![Q6 deepconf](timelines/q06_deepconf_confidence_timeline.png)

### Q7  ground truth 77

PeerConf: correct, 66K tokens

![Q7 peerconf](timelines/q07_peerconf_confidence_timeline.png)

DeepConf: correct, 264K tokens

![Q7 deepconf](timelines/q07_deepconf_confidence_timeline.png)

### Q8  ground truth 62

PeerConf: correct, 197K tokens

![Q8 peerconf](timelines/q08_peerconf_confidence_timeline.png)

DeepConf: correct, 627K tokens

![Q8 deepconf](timelines/q08_deepconf_confidence_timeline.png)

### Q9  ground truth 81

PeerConf: correct, 397K tokens

![Q9 peerconf](timelines/q09_peerconf_confidence_timeline.png)

DeepConf: correct, 632K tokens

![Q9 deepconf](timelines/q09_deepconf_confidence_timeline.png)

### Q10  ground truth 259

PeerConf: correct, 396K tokens

![Q10 peerconf](timelines/q10_peerconf_confidence_timeline.png)

DeepConf: correct, 625K tokens

![Q10 deepconf](timelines/q10_deepconf_confidence_timeline.png)

### Q11  ground truth 510

PeerConf: correct, 330K tokens

![Q11 peerconf](timelines/q11_peerconf_confidence_timeline.png)

DeepConf: correct, 566K tokens

![Q11 deepconf](timelines/q11_deepconf_confidence_timeline.png)

### Q12  ground truth 204

PeerConf: WRONG, answered `\dfrac{487}{3}`, 926K tokens

![Q12 peerconf](timelines/q12_peerconf_confidence_timeline.png)

DeepConf: WRONG, answered `\dfrac{487}{3}`, 855K tokens

![Q12 deepconf](timelines/q12_deepconf_confidence_timeline.png)

### Q13  ground truth 60

PeerConf: WRONG, answered `71`, 1,030K tokens

![Q13 peerconf](timelines/q13_peerconf_confidence_timeline.png)

DeepConf: WRONG, answered `62`, 915K tokens

![Q13 deepconf](timelines/q13_deepconf_confidence_timeline.png)

### Q14  ground truth 735

PeerConf: WRONG, answered `147`, 981K tokens

![Q14 peerconf](timelines/q14_peerconf_confidence_timeline.png)

DeepConf: WRONG, answered `969`, 1,027K tokens

![Q14 deepconf](timelines/q14_deepconf_confidence_timeline.png)

### Q15  ground truth 468

PeerConf: correct, 66K tokens

![Q15 peerconf](timelines/q15_peerconf_confidence_timeline.png)

DeepConf: correct, 101K tokens

![Q15 deepconf](timelines/q15_deepconf_confidence_timeline.png)

### Q16  ground truth 49

PeerConf: correct, 66K tokens

![Q16 peerconf](timelines/q16_peerconf_confidence_timeline.png)

DeepConf: correct, 133K tokens

![Q16 deepconf](timelines/q16_deepconf_confidence_timeline.png)

### Q17  ground truth 82

PeerConf: correct, 198K tokens

![Q17 peerconf](timelines/q17_peerconf_confidence_timeline.png)

DeepConf: correct, 335K tokens

![Q17 deepconf](timelines/q17_deepconf_confidence_timeline.png)

### Q18  ground truth 106

PeerConf: correct, 132K tokens

![Q18 peerconf](timelines/q18_peerconf_confidence_timeline.png)

DeepConf: correct, 262K tokens

![Q18 deepconf](timelines/q18_deepconf_confidence_timeline.png)

### Q19  ground truth 336

PeerConf: correct, 593K tokens

![Q19 peerconf](timelines/q19_peerconf_confidence_timeline.png)

DeepConf: correct, 499K tokens

![Q19 deepconf](timelines/q19_deepconf_confidence_timeline.png)

### Q20  ground truth 293

PeerConf: correct, 132K tokens

![Q20 peerconf](timelines/q20_peerconf_confidence_timeline.png)

DeepConf: correct, 273K tokens

![Q20 deepconf](timelines/q20_deepconf_confidence_timeline.png)

### Q21  ground truth 237

PeerConf: correct, 324K tokens

![Q21 peerconf](timelines/q21_peerconf_confidence_timeline.png)

DeepConf: correct, 262K tokens

![Q21 deepconf](timelines/q21_deepconf_confidence_timeline.png)

### Q22  ground truth 610

PeerConf: correct, 509K tokens

![Q22 peerconf](timelines/q22_peerconf_confidence_timeline.png)

DeepConf: correct, 599K tokens

![Q22 deepconf](timelines/q22_deepconf_confidence_timeline.png)

### Q23  ground truth 149

PeerConf: correct, 198K tokens

![Q23 peerconf](timelines/q23_peerconf_confidence_timeline.png)

DeepConf: correct, 495K tokens

![Q23 deepconf](timelines/q23_deepconf_confidence_timeline.png)

### Q24  ground truth 907

PeerConf: correct, 264K tokens

![Q24 peerconf](timelines/q24_peerconf_confidence_timeline.png)

DeepConf: correct, 398K tokens

![Q24 deepconf](timelines/q24_deepconf_confidence_timeline.png)

### Q25  ground truth 113

PeerConf: correct, 263K tokens

![Q25 peerconf](timelines/q25_peerconf_confidence_timeline.png)

DeepConf: correct, 389K tokens

![Q25 deepconf](timelines/q25_deepconf_confidence_timeline.png)

### Q26  ground truth 19

PeerConf: correct, 264K tokens

![Q26 peerconf](timelines/q26_peerconf_confidence_timeline.png)

DeepConf: correct, 382K tokens

![Q26 deepconf](timelines/q26_deepconf_confidence_timeline.png)

### Q27  ground truth 248

PeerConf: WRONG, answered `208`, 1,007K tokens

![Q27 peerconf](timelines/q27_peerconf_confidence_timeline.png)

DeepConf: WRONG, answered `208`, 869K tokens

![Q27 deepconf](timelines/q27_deepconf_confidence_timeline.png)

### Q28  ground truth 104

PeerConf: correct, 198K tokens

![Q28 peerconf](timelines/q28_peerconf_confidence_timeline.png)

DeepConf: correct, 462K tokens

![Q28 deepconf](timelines/q28_deepconf_confidence_timeline.png)

### Q29  ground truth 240

PeerConf: WRONG, answered `188`, 504K tokens

![Q29 peerconf](timelines/q29_peerconf_confidence_timeline.png)

DeepConf: WRONG, answered `188`, 712K tokens

![Q29 deepconf](timelines/q29_deepconf_confidence_timeline.png)

