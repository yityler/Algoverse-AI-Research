# MATH-500 — PeerConf probe interval: 4096 vs 512

Run requested by Mofe (Slack, 2026-08-19): *"run math-500 on peerconf with the new code
and with a window of 256 like before but change the probe to every 512 tokens."*

2× H200, DeepSeek-R1-0528-Qwen3-8B, Q0–Q24, 32-trace budget, 16 seats, 64k cap,
`WINDOW=256`, consensus 0.95, temperature 0.6. PeerConf only.

**Three runs are compared here, not two.** The obvious comparison — the new probe/512 run
against the existing probe/4096 run — is confounded, because that older run was produced by
code 38 commits behind. So a **control** was run: probe/4096 on current code, same commit
as the probe/512 run (`8057e78`). That isolates the probe interval from the code change.

| | probe/4096 old code | probe/4096 **control** | probe/512 |
|---|---|---|---|
| commit | `88c4294` | `8057e78` | `8057e78` |
| Total tokens | 1,928,910 | 1,851,969 | **1,291,913** |
| Mean tokens / question | 77,156 | 74,078 | 51,676 |
| Traces launched | 595 | 466 | 493 |
| Probes fired | 253 | 233 | 1,159 |
| Probe tokens | 3,774 | 3,431 | 18,548 |
| — as % of run | 0.20% | 0.19% | 1.44% |
| Graduated early | 33 | 33 | 85 |
| Cut at the bar | 191 | 16 | 33 |
| Ballots cast | 84 | 75 | 104 |
| — fewest on any question | 1 | 3 | 3 |
| Questions with zero cuts | 7 | 22 | 21 |
| Accuracy (`lenient_equal`) | 25/25 | 25/25 | 25/25 |
| Wall clock | 1,003 s | 1,016 s | 711 s |

## The result, now single-variable

Against its proper control, **probing every 512 tokens instead of every 4096 cuts token
spend by 30.2% and raises the number of ballots by 38.7%, with accuracy unchanged.**

Wall clock falls 30% too (1,016 s → 711 s). The extra probing costs 15,117 additional probe
tokens, 1.2% of the run.

Cheaper *and* better-supported is the claim worth making. It is not a speed/quality trade.

## What belongs to the code change, not the probe interval

The old run differs from the control by 38 commits, and several effects that look like
probe-interval wins are actually code. Reading the first two columns:

- **Token spend: −4.0%.** The code change is nearly neutral on cost. The 30% belongs to the
  probe interval.
- **Cuts at the bar: 191 → 16.** The collapse in cutting is *entirely* the code. Questions
  finishing with zero cuts go 7 → 22 before the probe interval is touched at all.
- **The single-ballot case: 1 → 3.** Q5 was decided on one ballot under old code. Current
  code puts the floor at 3 regardless of probe interval.
- **Accuracy 23/25 → 24/25 as the pipeline reports it.** This is the grader, not the method.
  Both runs emit the identical Q0 string `\left(3,\ \dfrac{\pi}{2}\right)` against gold
  `\left( 3, \frac{\pi}{2} \right)`; old code scored it wrong, current code scores it right.
  Under `aws/grading.py` `lenient_equal` **all three runs are 25/25**. Never report +1.

What the probe interval actually owns: **tokens (−30.2%), graduations (33 → 85), ballots
(75 → 104), wall clock (−30%)**.

## Per question

Δ is the probe-interval effect — control against probe/512, same code.

| Q | old code | control | probe/512 | Δ | ballots (old/ctrl/512) |
|---|---|---|---|---|---|
| 0 | 17,237 | 17,261 | 17,265 | 0% | 3 / 3 / 3 |
| 1 | 65,843 | 65,981 | 33,368 | −49% | 3 / 3 / 3 |
| 2 | 29,057 | 27,828 | 28,611 | +3% | 3 / 3 / 3 |
| 3 | 21,201 | 20,480 | 19,345 | −6% | 3 / 3 / 3 |
| 4 | 64,989 | 65,954 | 43,845 | −34% | 3 / 3 / **16** |
| 5 | 27,769 | 42,204 | 32,973 | −22% | **1** / 3 / 3 |
| 6 | 58,576 | 65,765 | 32,946 | −50% | 3 / 3 / 3 |
| 7 | 65,996 | 65,583 | 33,133 | −49% | 3 / 3 / 3 |
| 8 | 28,389 | 18,718 | 18,555 | −1% | 3 / 3 / 3 |
| 9 | 264,283 | 264,816 | 262,420 | −1% | 3 / 3 / 3 |
| 10 | 131,522 | 131,483 | 41,336 | **−69%** | 3 / 3 / 3 |
| 11 | 122,517 | 129,021 | 75,860 | −41% | 3 / 3 / 3 |
| 12 | 65,765 | 65,539 | 33,075 | −50% | 3 / 3 / 3 |
| 13 | 11,643 | 10,360 | 10,289 | −1% | 3 / 3 / 3 |
| 14 | 60,823 | 60,946 | 33,462 | −45% | 3 / 3 / 3 |
| 15 | 60,422 | 54,333 | 33,135 | −39% | 3 / 3 / 3 |
| 16 | 31,234 | 33,021 | 32,902 | 0% | 3 / 3 / 3 |
| 17 | 131,661 | 66,880 | 50,512 | −24% | 3 / 3 / 3 |
| 18 | 353,281 | 262,936 | 180,666 | −31% | 14 / **3** / **11** |
| 19 | 65,964 | 66,043 | 33,151 | −50% | 3 / 3 / 3 |
| 20 | 14,435 | 9,887 | 9,012 | −9% | 3 / 3 / 3 |
| 21 | 66,340 | 131,388 | 136,829 | +4% | 3 / 3 / **11** |
| 22 | 50,920 | 48,990 | 32,871 | −33% | 3 / 3 / 3 |
| 23 | 53,123 | 60,853 | 32,928 | −46% | 3 / 3 / 3 |
| 24 | 65,920 | 65,699 | 33,424 | −49% | 3 / 3 / 3 |
| **tot** | **1,928,910** | **1,851,969** | **1,291,913** | **−30.2%** | 84 / 75 / **104** |

**21 of 25 questions get cheaper**, 2 are flat (Q0, Q16), and only Q2 (+2.8%) and Q21
(+4.1%) rise — both marginally. The largest single saving is Q10 at −69%.

### Q18 — the question the paper's accuracy claim rests on

Worth calling out separately. Under current code at probe/4096, **Q18 decides on only 3
ballots** — down from 14 under old code. Probe/512 brings it back to **11 ballots while
spending 31% fewer tokens** (262,936 → 180,666).

That matters because Q18 is the sole question where PeerConf and DeepConf disagree, and
DeepConf decides it on a 4-way tie among 4 singleton ballots — see
`../math500_w256/Q18_VOTING_POOL.md`. Deciding it on 11 ballots rather than 3 is the
difference between a defensible result and another coin flip.

### Q21 — the apparent regression is not the probe interval

Q21 doubles from 66,340 to 136,829 against the *old* run, which is what an uncontrolled
comparison shows. Against the control it rises **4%**. The doubling happened in the code
change (66,340 → 131,388), and probe/512 is nearly neutral on it while lifting ballots from
3 to 11. There is no probe-interval regression on Q21.

Q5 is the same mistake in the other direction: it looks like a +19% regression against the
old run, but the code change took it 27,769 → 42,204 and probe/512 brought it **back down
22%** to 32,973.

## Reproducing

```bash
python aws/compare_runs.py \
  "old=results/math500/math500_w256/peerconf.log" \
  "control=results/math500/math500_w256_p4096/peerconf.log" \
  "p512=results/math500/math500_w256_p512/peerconf.log"
```

Both new runs: `modal run --detach aws/modal_run.py --window 256 --probe-every {4096,512} --arms peerconf`.

## Files

- `peerconf.log`, `peerconf_out/` — this run's log, 25 charts, 25 pkls
- `../math500_w256_p4096/` — the control run
- 62MB `vllm_server.log` for each was left on the Modal volume
