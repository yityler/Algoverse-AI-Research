# AIME25

PeerConf-low on all 30 questions. DeepConf-low at the same budget is still to run.

## Results

| Model | Dataset | Token | Time | Acc | Mean token/Q |
|---|---|---|---|---|---|
| DeepSeek-8B | AIME25 (Q0-29) | 11.66M | 145 min | 86.7% | 389K |
| | correct subset (26 Q) | 6.85M | 72 min | 100% | 263K |

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.
Time = generation wall-clock on 2x H200 SXM, excludes server startup.

The four wrong answers (Q13, Q14, Q27, Q29) cost 4.82M tokens, 41% of the run,
so a correct answer averages 263K tokens and a wrong one averages 1.20M.

## If we counted only the first k votes

Accuracy against the number of finished traces allowed to vote, replayed from
the same run. Nothing else changes.

| k | Acc | Voter token | Est. total | vs full run |
|---|---|---|---|---|
| 3 | 24/30 (80%) | 1.47M | 3.67M | 31% |
| 4 | 25/30 (83%) | 1.78M | 4.44M | 38% |
| **8** | **26/30 (87%)** | **3.01M** | **7.52M** | **64%** |
| 10 | 26/30 (87%) | 3.51M | 8.78M | 75% |
| all (32) | 26/30 (87%) | 4.66M | 11.66M | 100% |

Accuracy saturates at k=8: every vote after the eighth changed nothing, so
stopping there costs about 36% fewer tokens at the same 26/30.

Voter token counts only the traces that voted. Those were 40% of everything the
run generated, the rest going to traces that were cut, truncated or drained, so
est. total scales the voter figure by that share. It is an estimate, not a
measurement: the in-flight spend of a run that actually stopped at k was never
observed.

k=8 is read off these 30 questions and has not been checked on a held-out set.

## Confidence timelines

One figure per question. Each line is a trace's sliding-window confidence
over its own life, coloured by how it ended. The blue band is the
self-calibrating bar from armed to final.

### Q0  ground truth 70, correct, 66K tokens

![Q0](timelines/q0_confidence_timeline.png)

### Q1  ground truth 588, correct, 132K tokens

![Q1](timelines/q1_confidence_timeline.png)

### Q2  ground truth 16, correct, 66K tokens

![Q2](timelines/q2_confidence_timeline.png)

### Q3  ground truth 117, correct, 66K tokens

![Q3](timelines/q3_confidence_timeline.png)

### Q4  ground truth 279, correct, 132K tokens

![Q4](timelines/q4_confidence_timeline.png)

### Q5  ground truth 504, correct, 66K tokens

![Q5](timelines/q5_confidence_timeline.png)

### Q6  ground truth 821, correct, 491K tokens

![Q6](timelines/q6_confidence_timeline.png)

### Q7  ground truth 77, correct, 66K tokens

![Q7](timelines/q7_confidence_timeline.png)

### Q8  ground truth 62, correct, 197K tokens

![Q8](timelines/q8_confidence_timeline.png)

### Q9  ground truth 81, correct, 712K tokens

![Q9](timelines/q9_confidence_timeline.png)

### Q10  ground truth 259, correct, 396K tokens

![Q10](timelines/q10_confidence_timeline.png)

### Q11  ground truth 510, correct, 330K tokens

![Q11](timelines/q11_confidence_timeline.png)

### Q12  ground truth 204, correct, 920K tokens

![Q12](timelines/q12_confidence_timeline.png)

### Q13  ground truth 60, WRONG, answered 71, 1792K tokens

![Q13](timelines/q13_confidence_timeline.png)

### Q14  ground truth 735, WRONG, answered 147, 981K tokens

![Q14](timelines/q14_confidence_timeline.png)

### Q15  ground truth 468, correct, 66K tokens

![Q15](timelines/q15_confidence_timeline.png)

### Q16  ground truth 49, correct, 66K tokens

![Q16](timelines/q16_confidence_timeline.png)

### Q17  ground truth 82, correct, 198K tokens

![Q17](timelines/q17_confidence_timeline.png)

### Q18  ground truth 106, correct, 132K tokens

![Q18](timelines/q18_confidence_timeline.png)

### Q19  ground truth 336, correct, 593K tokens

![Q19](timelines/q19_confidence_timeline.png)

### Q20  ground truth 293, correct, 132K tokens

![Q20](timelines/q20_confidence_timeline.png)

### Q21  ground truth 237, correct, 324K tokens

![Q21](timelines/q21_confidence_timeline.png)

### Q22  ground truth 610, correct, 509K tokens

![Q22](timelines/q22_confidence_timeline.png)

### Q23  ground truth 149, correct, 198K tokens

![Q23](timelines/q23_confidence_timeline.png)

### Q24  ground truth 907, correct, 264K tokens

![Q24](timelines/q24_confidence_timeline.png)

### Q25  ground truth 113, correct, 263K tokens

![Q25](timelines/q25_confidence_timeline.png)

### Q26  ground truth 19, correct, 264K tokens

![Q26](timelines/q26_confidence_timeline.png)

### Q27  ground truth 248, WRONG, answered 0, 1539K tokens

![Q27](timelines/q27_confidence_timeline.png)

### Q28  ground truth 104, correct, 198K tokens

![Q28](timelines/q28_confidence_timeline.png)

### Q29  ground truth 240, WRONG, answered 188, 504K tokens

![Q29](timelines/q29_confidence_timeline.png)
