# Benchmarks

One jsonl per benchmark, one question per line, always the same two fields:

```json
{"question": "Find the sum of all integer bases $b>9$ ...", "answer": "70"}
```

| file | questions | source |
|------|-----------|--------|
| `aime25.jsonl` | 30 | AIME 2025 |
| `hmmt25.jsonl` | 30 | [MathArena/hmmt_feb_2025](https://huggingface.co/datasets/MathArena/hmmt_feb_2025) |
| `math500.jsonl` | 500 | [HuggingFaceH4/MATH-500](https://huggingface.co/datasets/HuggingFaceH4/MATH-500) |
| `gsm8k.jsonl` | 1319 | [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) (test split) |

Regenerate any of them with `python benchmarks/fetch_benchmarks.py [name]`. It
uses the datasets-server HTTP API, so no extra packages are needed. GSM8K's
answer is reduced to the number after `####`; MATH-500 and HMMT keep the
dataset's own answer string, since `math_equal` does the grading and handles
LaTeX.

## Switching benchmark

Both run scripts read the `DATASET` env var and default to `aime25`:

```bash
DATASET=math500 python peerconf/cell2_run.py        # PeerConf
DATASET=gsm8k   python deepconf/cell2_deepconf.py   # DeepConf
```

Adding a fifth benchmark means dropping a `<name>.jsonl` here in the same schema
and passing `DATASET=<name>` — no code change.

## Which questions run

`QIDS` at the top of each cell2 takes `range(30)` for a span or `[6, 9]` for a
specific set. Asking for a question the benchmark doesn't have stops the run
outright, before anything generates, and names the valid range:

```
SystemExit: hmmt25 has 30 questions (0-29); QIDS asks for [30, 99]
```

Nothing is silently skipped, because a sweep that quietly shortened itself would
look like a complete one afterwards.

## Output filenames

`aime25` results keep the original bare names (`q6_bar_cs_looph.pkl`) so the
existing sweep's pkls still count as done. Every other benchmark prefixes its
own name (`math500_q6_bar_cs_looph.pkl`), so two benchmarks can share one output
directory without colliding or falsely skipping each other. The cell3 timeline
viewers read the prefix and also take `DATASET`, drawing one benchmark at a time.
