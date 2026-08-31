# Raw DeepConf-low pkls — HMMT25, DeepSeek-R1-0528-Qwen3-8B

The 30 raw run artifacts (one per question, Q0–Q29) behind the DeepConf-low arm
in [../README.md](../README.md). Committed as-is for per-path granularity:
every trace's answer and token count, not just the aggregate figures.

Raw pkls are normally kept off git in this repo and left on the Modal Volume
(`peerconf-out:/deepconf_out/`). This directory is a deliberate exception.

## What these are

- Method `deepconf-low`, dataset `hmmt25`, model `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B`.
- `CONFIDENCE_PERCENTILE` 10, `WINDOW` 2048, `CONSENSUS` 0.95, 64k-token cap,
  temperature 0.6 / top-p 0.95 / top-k off, 2x H200, `--tensor-parallel-size 2`.
- Budget 32 traces / question over 16 seats: **16 warmup traces on every one of
  the 30 questions** (480 total), plus an online wave on the 12 questions where
  consensus did not settle during warmup (192 more traces, 672 in all).

## Shape

Each pkl unpickles to a dict:

| key | |
|---|---|
| `qid` | int, 0–29, matches the filename |
| `gt` | the benchmark's own answer string |
| `config` | MODE, MODEL, DATASET, CONFIDENCE_PERCENTILE, WARMUP_TRACES, TOTAL_BUDGET, WINDOW, CONSENSUS, MAX_TOK_TRACE, conf_bar |
| `voting` | the run's own tallies under each voting rule |
| `tokens` | total generated tokens for the question |
| `time_s` | wall clock for the question |
| `warmup_min_confs` | the 16 warmup min-window confidences the bar is set from |
| `conf_bar` | the frozen 10th-percentile bar |
| `traces` | list of per-trace dicts |

Each trace carries `id`, `phase` (`warmup` or `online`), `prompt`, `text`,
`answer`, `confs`, `toks_gen`, `status`. **Filter on `phase == "warmup"` to get
the 16 unmanaged traces per question** — the warmup phase is run fully and never
judged, so those 16 are an unfiltered self-consistency sample. The `online`
traces are not: they exist only where consensus had not settled, and they are
subject to the bar and the kill path.

3 of the 480 warmup traces produced no boxed answer (hit the cap), so a plain
warmup vote has 477 usable ballots, not 480.

## Already computed from these

SC@16, a plain majority vote over the warmup traces with no bar applied:

| Method | Acc | Total tokens | Mean token/Q |
|---|---|---|---|
| SC@16 (plain majority) | 20/30 (66.7%) | 14,387,189 | 479K |

That 14,387,189 is the sum of `toks_gen` over the `phase == "warmup"` traces in
these 30 files, and it is a strict subset of the DeepConf arm's own 17,314,634.
The grading was validated rather than assumed: replicating DeepConf's own
bar-filtered ballot pool reproduces its reported majority on all 18 questions
where the online wave never ran, which is where the two must agree by
construction. See "SC@16, computed from DeepConf's own warmup traces" in
[../README.md](../README.md).

## Why they are here

Tyler is combining these 16 warmup paths per question with a separate SC@32 run
to form a plain majority vote over all 32 paths per question. That needs the
per-path answers and token counts, which the summary tables do not carry.

Note that these warmup traces share the DeepConf run's sampling stream; they are
not an independent SC draw. Any vote combining them with a separate run should
say so.
