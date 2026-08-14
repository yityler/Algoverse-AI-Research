# MATH500

peerconf-low and deepconf-low on 25 questions (Q0-24), matched settings.

## Results

| Method | Model | Dataset | Token | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | DeepSeek-8B | MATH500 (Q0-24) | 1.93M | 92.0% | 77K |
| DeepConf-low | DeepSeek-8B | MATH500 (Q0-24) | 3.22M | 88.0% | 129K |

PeerConf spends 40.0% fewer tokens and answers 1 more question.
Accuracy is the min-window-weighted vote in both arms.

Budget 32 traces/question, 16 seats, 64k-token cap, one run per question.

Average length of a path:

PeerConf - 3,235 tokens

DeepConf - 7,729 tokens


## Per question

| Q | GT | PeerConf | DeepConf | PeerConf tokens | DeepConf tokens | Saving |
|---|---|---|---|---|---|---|
| 0 | \left( 3, \frac{.. | no | no | 17,237 | 22,508 | 23.4% |
| 1 | p - q | yes | yes | 65,843 | 153,726 | 57.2% |
| 2 | \frac{14}{3} | yes | yes | 29,057 | 35,814 | 18.9% |
| 3 | 9 | yes | yes | 21,201 | 25,539 | 17.0% |
| 4 | \text{Evelyn} | yes | yes | 64,989 | 78,552 | 17.3% |
| 5 | 42 | yes | yes | 27,769 | 67,006 | 58.6% |
| 6 | 27 | yes | yes | 58,576 | 88,041 | 33.5% |
| 7 | 90^\circ | no | no | 65,996 | 87,103 | 24.2% |
| 8 | 3\sqrt{13} | yes | yes | 28,389 | 23,027 | -23.3% |
| 9 | 4 | yes | yes | 264,283 | 374,430 | 29.4% |
| 10 | 2220 | yes | yes | 131,522 | 175,703 | 25.1% |
| 11 | \frac{3}{56} | yes | yes | 122,517 | 180,516 | 32.1% |
| 12 | 284 | yes | yes | 65,765 | 94,998 | 30.8% |
| 13 | 5 | yes | yes | 11,643 | 41,853 | 72.2% |
| 14 | \sqrt{51} | yes | yes | 60,823 | 77,987 | 22.0% |
| 15 | 6 - 5i | yes | yes | 60,422 | 74,791 | 19.2% |
| 16 | -50 | yes | yes | 31,234 | 40,973 | 23.8% |
| 17 | \pi | yes | yes | 131,661 | 289,851 | 54.6% |
| 18 | 28 | yes | no | 353,281 | 472,832 | 25.3% |
| 19 | 3 | yes | yes | 65,964 | 193,991 | 66.0% |
| 20 | 6+9i | yes | yes | 14,435 | 15,172 | 4.9% |
| 21 | 13535 | yes | yes | 66,340 | 295,125 | 77.5% |
| 22 | 5 | yes | yes | 50,920 | 78,326 | 35.0% |
| 23 | x=5 | yes | yes | 53,123 | 77,868 | 31.8% |
| 24 | 10 | yes | yes | 65,920 | 149,727 | 56.0% |
