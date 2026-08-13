# AIME25

peerconf-low on all 30 questions. deepconf coming soon.

## Results

| Model | Dataset | Token | Time | Acc | Mean token/Q |
|---|---|---|---|---|---|
| DeepSeek-8B | AIME25 (Q0-29) | 10.39M | 125 min | 86.7% | 346K |
| | correct subset (26 Q) | 6.84M | 72 min | 100% | 263K |

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.
Time = generation wall-clock on 2x H200 SXM, excludes server startup.

The four wrong answers (Q13, Q14, Q27, Q29) cost 3.55M tokens, 34% of the run,
so a correct answer averages 263K tokens and a wrong one averages 887K.

## Confidence timelines

One figure per question. Each line is a trace's sliding-window confidence
over its own life, coloured by how it ended. The blue band is the
self-calibrating bar from armed to final.

### Q0  ground truth 70, correct, 66K tokens

![Q0](timelines/q00_peerconf_confidence_timeline.png)

### Q1  ground truth 588, correct, 132K tokens

![Q1](timelines/q01_peerconf_confidence_timeline.png)

### Q2  ground truth 16, correct, 66K tokens

![Q2](timelines/q02_peerconf_confidence_timeline.png)

### Q3  ground truth 117, correct, 66K tokens

![Q3](timelines/q03_peerconf_confidence_timeline.png)

### Q4  ground truth 279, correct, 132K tokens

![Q4](timelines/q04_peerconf_confidence_timeline.png)

### Q5  ground truth 504, correct, 66K tokens

![Q5](timelines/q05_peerconf_confidence_timeline.png)

### Q6  ground truth 821, correct, 491K tokens

![Q6](timelines/q06_peerconf_confidence_timeline.png)

### Q7  ground truth 77, correct, 66K tokens

![Q7](timelines/q07_peerconf_confidence_timeline.png)

### Q8  ground truth 62, correct, 197K tokens

![Q8](timelines/q08_peerconf_confidence_timeline.png)

### Q9  ground truth 81, correct, 712K tokens

![Q9](timelines/q09_peerconf_confidence_timeline.png)

### Q10  ground truth 259, correct, 396K tokens

![Q10](timelines/q10_peerconf_confidence_timeline.png)

### Q11  ground truth 510, correct, 330K tokens

![Q11](timelines/q11_peerconf_confidence_timeline.png)

### Q12  ground truth 204, correct, 911K tokens

![Q12](timelines/q12_peerconf_confidence_timeline.png)

### Q13  ground truth 60, WRONG, answered 71, 1032K tokens

![Q13](timelines/q13_peerconf_confidence_timeline.png)

### Q14  ground truth 735, WRONG, answered 147, 981K tokens

![Q14](timelines/q14_peerconf_confidence_timeline.png)

### Q15  ground truth 468, correct, 66K tokens

![Q15](timelines/q15_peerconf_confidence_timeline.png)

### Q16  ground truth 49, correct, 66K tokens

![Q16](timelines/q16_peerconf_confidence_timeline.png)

### Q17  ground truth 82, correct, 198K tokens

![Q17](timelines/q17_peerconf_confidence_timeline.png)

### Q18  ground truth 106, correct, 132K tokens

![Q18](timelines/q18_peerconf_confidence_timeline.png)

### Q19  ground truth 336, correct, 593K tokens

![Q19](timelines/q19_peerconf_confidence_timeline.png)

### Q20  ground truth 293, correct, 132K tokens

![Q20](timelines/q20_peerconf_confidence_timeline.png)

### Q21  ground truth 237, correct, 324K tokens

![Q21](timelines/q21_peerconf_confidence_timeline.png)

### Q22  ground truth 610, correct, 509K tokens

![Q22](timelines/q22_peerconf_confidence_timeline.png)

### Q23  ground truth 149, correct, 198K tokens

![Q23](timelines/q23_peerconf_confidence_timeline.png)

### Q24  ground truth 907, correct, 264K tokens

![Q24](timelines/q24_peerconf_confidence_timeline.png)

### Q25  ground truth 113, correct, 263K tokens

![Q25](timelines/q25_peerconf_confidence_timeline.png)

### Q26  ground truth 19, correct, 264K tokens

![Q26](timelines/q26_peerconf_confidence_timeline.png)

### Q27  ground truth 248, WRONG, answered 208, 1031K tokens

![Q27](timelines/q27_peerconf_confidence_timeline.png)

### Q28  ground truth 104, correct, 198K tokens

![Q28](timelines/q28_peerconf_confidence_timeline.png)

### Q29  ground truth 240, WRONG, answered 188, 504K tokens

![Q29](timelines/q29_peerconf_confidence_timeline.png)
