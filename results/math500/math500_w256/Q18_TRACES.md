# Q18 — Analysis of Traces

The most expensive question in the run and the only one where the model genuinely
disagreed with itself. Full trace-by-trace breakdown.

## The question

> $\overline{BC}$ is parallel to the segment through $A$, and $AB = BC$. What is the number of degrees represented by $x$?

[asy]
draw((0,0)--(10,0));
draw((0,3)--(10,3));
draw((2,3)--(8,0));
draw((2,3)--(4,0));
label("$A$",(2,3),N);
label("$B$",(4,0),S);
label("$C$",(8,0),S);
label("$124^{\circ}$",(2,3),SW);
label("$x^{\circ}$",(4.5,3),S);
[/asy]

**Correct answer:** `28`

## Outcome

| | PeerConf | DeepConf |
|---|---|---|
| answer | `28` | `68` |
| correct | yes | no |
| tokens | 353,281 | 472,832 |
| traces | 32 | 32 |
| bar | live, 14 updates | frozen at 11.695 |

PeerConf used **25% fewer** tokens.

---

## PeerConf — 32 traces

`wave 1` are the 16 traces that opened the race; the rest took freed seats after a
cut. The bar was live and updated as finishers arrived.

| # | wave | status | tokens | readings | worst reading | answer | correct |
|---|---|---|---|---|---|---|---|
| 0 | 1 | stopped | 12,493 | 12238 | 11.41 | — |  |
| 1 | 1 | finished | 8,202 | 7947 | 11.41 | `68` |  |
| 2 | 1 | finished | 28,192 | 27937 | 10.79 | `56` |  |
| 3 | 1 | finished | 28,781 | 28526 | 11.42 | `68` |  |
| 4 | 1 | finished | 12,307 | 12052 | 11.60 | `28` | yes |
| 5 | 1 | finished | 12,298 | 12043 | 11.80 | `28` | yes |
| 6 | 1 | finished | 24,700 | 24445 | 11.39 | `56` |  |
| 7 | 1 | finished | 23,615 | 23360 | 11.14 | `30` |  |
| 8 | 1 | stopped | 9,335 | 9080 | 11.36 | — |  |
| 9 | 1 | finished | 20,603 | 20348 | 11.35 | `28` | yes |
| 10 | 1 | finished | 23,395 | 23140 | 11.33 | `124` |  |
| 11 | 1 | finished | 12,322 | 12067 | 11.62 | `56` |  |
| 12 | 1 | finished | 24,682 | 24427 | 11.24 | `28` | yes |
| 13 | 1 | finished | 8,238 | 7983 | 11.24 | `28` | yes |
| 14 | 1 | finished | 22,854 | 22599 | 11.30 | `124` |  |
| 15 | 1 | finished | 8,237 | 7982 | 11.00 | `28` | yes |
| 16 | repl | stopped | 1,585 | 1330 | 11.36 | — |  |
| 17 | repl | abandoned | 20,532 | 20277 | 11.69 | — |  |
| 18 | repl | stopped | 2,828 | 2573 | 11.10 | — |  |
| 19 | repl | abandoned | 19,432 | 19177 | 11.49 | — |  |
| 20 | repl | stopped | 2,716 | 2461 | 11.61 | — |  |
| 21 | repl | stopped | 531 | 276 | 11.38 | — |  |
| 22 | repl | stopped | 2,400 | 2145 | 11.67 | — |  |
| 23 | repl | stopped | 1,624 | 1369 | 11.70 | — |  |
| 24 | repl | stopped | 2,024 | 1769 | 11.71 | — |  |
| 25 | repl | stopped | 1,152 | 897 | 11.68 | — |  |
| 26 | repl | stopped | 4,840 | 4585 | 11.71 | — |  |
| 27 | repl | stopped | 2,527 | 2272 | 11.68 | — |  |
| 28 | repl | stopped | 2,214 | 1959 | 11.70 | — |  |
| 29 | repl | stopped | 1,969 | 1714 | 11.70 | — |  |
| 30 | repl | stopped | 2,957 | 2702 | 11.71 | — |  |
| 31 | repl | stopped | 2,962 | 2707 | 11.71 | — |  |

**Summary.** {'stopped': 16, 'finished': 14, 'abandoned': 2}. Median trace 8,237 tokens, longest 28,781. 14 produced an answer.

Ballots cast:

- `28` x6 **(correct)**
- `56` x3 
- `68` x2 
- `124` x2 
- `30` x1 

258,426 of 353,281 tokens (73%) went into traces that produced an answer.

---

## DeepConf — 32 traces

`warmup` traces run to completion and are never judged; the bar freezes at the
10th percentile of their worst readings, here **11.695**. `online`
traces are measured against it from the first full window.

| # | phase | status | tokens | readings | worst reading | vs bar | answer | correct |
|---|---|---|---|---|---|---|---|---|
| 0 | warmup | finished | 23,270 | 23015 | 11.35 | below | `28` | yes |
| 1 | warmup | finished | 27,443 | 27188 | 11.49 | below | `124` |  |
| 2 | warmup | finished | 24,784 | 24529 | 11.42 | below | `62` |  |
| 3 | warmup | finished | 24,702 | 24447 | 11.31 | below | `28` | yes |
| 4 | warmup | finished | 25,727 | 25472 | 11.29 | below | `28` | yes |
| 5 | warmup | finished | 27,062 | 26807 | 11.41 | below | `124` |  |
| 6 | warmup | finished | 27,154 | 26899 | 11.65 | below | `56` |  |
| 7 | warmup | finished | 22,585 | 22330 | 10.79 | below | `56` |  |
| 8 | warmup | finished | 26,466 | 26211 | 12.11 | above | `68` |  |
| 9 | warmup | finished | 27,105 | 26850 | 11.31 | below | `56` |  |
| 10 | warmup | finished | 26,312 | 26057 | 11.29 | below | `56` |  |
| 11 | warmup | finished | 24,236 | 23981 | 11.74 | above | `28` | yes |
| 12 | warmup | finished | 25,249 | 24994 | 11.19 | below | `124` |  |
| 13 | warmup | finished | 21,145 | 20890 | 11.42 | below | `124` |  |
| 14 | warmup | finished | 22,001 | 21746 | 11.61 | below | `28` | yes |
| 15 | warmup | finished | 30,629 | 30374 | 11.32 | below | `68` |  |
| 16 | online | stopped | 1,482 | 1227 | 11.68 | below | — |  |
| 17 | online | stopped | 2,752 | 2497 | 11.69 | below | — |  |
| 18 | online | stopped | 1,469 | 1214 | 11.69 | below | — |  |
| 19 | online | stopped | 2,659 | 2404 | 11.69 | below | — |  |
| 20 | online | finished | 16,128 | 15873 | 11.85 | above | `124` |  |
| 21 | online | stopped | 660 | 405 | 11.69 | below | — |  |
| 22 | online | stopped | 3,286 | 3031 | 11.68 | below | — |  |
| 23 | online | stopped | 2,381 | 2126 | 11.68 | below | — |  |
| 24 | online | finished | 23,714 | 23459 | 11.78 | above | `56` |  |
| 25 | online | stopped | 1,006 | 751 | 11.69 | below | — |  |
| 26 | online | stopped | 1,034 | 779 | 11.69 | below | — |  |
| 27 | online | stopped | 1,902 | 1647 | 11.69 | below | — |  |
| 28 | online | stopped | 1,882 | 1627 | 11.69 | below | — |  |
| 29 | online | stopped | 1,056 | 801 | 11.68 | below | — |  |
| 30 | online | stopped | 1,741 | 1486 | 11.67 | below | — |  |
| 31 | online | stopped | 3,810 | 3555 | 11.67 | below | — |  |

**Summary.** {'finished': 18, 'stopped': 14}. Median trace 21,573 tokens, longest 30,629. 18 produced an answer.

Ballots cast:

- `28` x5 **(correct)**
- `124` x5 
- `56` x5 
- `68` x2 
- `62` x1 

445,712 of 472,832 tokens (94%) went into traces that produced an answer.

---

## What the two tables show

**PeerConf killed 16 traces and kept 14 ballots. DeepConf killed 14 and kept 18.**

DeepConf's sixteen warm-up traces all ran to completion before the bar existed, which is
where its extra cost comes from. PeerConf started judging as soon as its first finisher
armed the bar, and cut steadily from then on.

The wrong answers are not noise. They cluster on specific values, which means traces are
making the same geometric misstep rather than failing randomly — the disagreement is
structured, and a confidence cutoff has something real to separate.

