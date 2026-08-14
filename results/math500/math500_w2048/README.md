# MATH-500 — PeerConf only (WINDOW = 2048)

**Single arm. DeepConf crashed on this run, so there is no comparison here.**

## Results

| Method | Model | Dataset | Token | Acc | Mean token/Q |
|---|---|---|---|---|---|
| PeerConf-low | DeepSeek-8B | MATH500 (Q0-24) | 2.27M | 92.0% | 91K |

Budget 32 traces/question, 16 seats, 64k-token cap, WINDOW 2048, 2x H200. Accuracy is the min-window-weighted vote, graded with math_equal.

## Read this before using the numbers

**The confidence window was wider than most traces.** Median trace here is 2,335 tokens against a 2048-token window, and a score only exists once a full window fills. So **268 of 659 traces (41%) produced no confidence signal at all** and could never be judged or cut.

On Q0, Q8, Q13, Q20 the bar never armed and nothing was cut. The same cause crashed DeepConf outright: all 16 of its warm-up traces were shorter than the window, so the percentile got an empty array.

These settings are tuned for AIME, where traces run 15k-30k tokens. A re-run at WINDOW 256 is the comparable experiment.

**Two questions are graded wrong that the model got right.** Q0 gold is `\left( 3, \frac{\pi}{2} \right)` and the model wrote `\left(3,\ \dfrac{\pi}{2}\right)` on 17 of 18 traces. Q7 gold is `90^\circ`, the model said `90`. `math_equal` rejects both. True score is 25/25; the pipeline reports 23/25.

## Per question

| Q | GT | Answer | Correct | Tokens | Launched | Finished | Cut | Bar armed |
|---|---|---|---|---|---|---|---|---|
| 0 | `\left( 3, \frac{\pi}{2} ` | `(3,\ \dfrac{\pi}{2})` | NO | 35,286 | 32 | 18 | 0 | NO |
| 1 | `p - q` | `p - q` | yes | 66,224 | 18 | 3 | 0 | yes |
| 2 | `\frac{14}{3}` | `\dfrac{14}{3}` | yes | 32,951 | 22 | 7 | 0 | yes |
| 3 | `9` | `9` | yes | 32,873 | 29 | 14 | 0 | yes |
| 4 | `\text{Evelyn}` | `\text{Evelyn}` | yes | 103,089 | 32 | 2 | 29 | yes |
| 5 | `42` | `42` | yes | 44,953 | 22 | 3 | 4 | yes |
| 6 | `27` | `27` | yes | 65,530 | 20 | 3 | 2 | yes |
| 7 | `90^\circ` | `90` | NO | 66,128 | 22 | 3 | 4 | yes |
| 8 | `3\sqrt{13}` | `3\sqrt{13}` | yes | 34,981 | 32 | 17 | 0 | NO |
| 9 | `4` | `4` | yes | 327,333 | 19 | 3 | 1 | yes |
| 10 | `2220` | `2220` | yes | 131,520 | 27 | 3 | 9 | yes |
| 11 | `\frac{3}{56}` | `\dfrac{3}{56}` | yes | 131,332 | 30 | 3 | 12 | yes |
| 12 | `284` | `284` | yes | 87,572 | 32 | 1 | 31 | yes |
| 13 | `5` | `5` | yes | 25,165 | 32 | 17 | 0 | NO |
| 14 | `\sqrt{51}` | `\sqrt{51}` | yes | 56,432 | 25 | 3 | 7 | yes |
| 15 | `6 - 5i` | `6-5i` | yes | 87,966 | 32 | 1 | 31 | yes |
| 16 | `-50` | `-50` | yes | 33,656 | 21 | 6 | 0 | yes |
| 17 | `\pi` | `\pi` | yes | 131,367 | 22 | 3 | 4 | yes |
| 18 | `28` | `28` | yes | 427,788 | 32 | 16 | 11 | yes |
| 19 | `3` | `3` | yes | 66,023 | 29 | 3 | 11 | yes |
| 20 | `6+9i` | `6+9i` | yes | 22,929 | 32 | 17 | 0 | NO |
| 21 | `13535` | `13535` | yes | 66,308 | 20 | 3 | 2 | yes |
| 22 | `5` | `5` | yes | 73,766 | 31 | 3 | 13 | yes |
| 23 | `x=5` | `5` | yes | 50,527 | 28 | 3 | 10 | yes |
| 24 | `10` | `10` | yes | 65,704 | 18 | 3 | 0 | yes |
