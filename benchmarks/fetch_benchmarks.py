"""Regenerate the benchmark jsonl files from Hugging Face.

    python benchmarks/fetch_benchmarks.py            # all of them
    python benchmarks/fetch_benchmarks.py gsm8k      # just one

Every file lands in this folder as {"question": ..., "answer": ...} per line —
the schema cell2_run.py / cell2_deepconf.py read, and the same one aime25.jsonl
already uses, so a new benchmark is a filename swap and nothing else.

Answers are stored as the model is expected to box them: GSM8K's chain of
thought is stripped down to the number after "####", MATH-500 and HMMT keep the
dataset's own answer string (math_equal does the grading, so LaTeX is fine).

Uses the datasets-server HTTP API rather than the `datasets` package so this
runs on a bare python with no extra installs.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = 100          # datasets-server caps a rows request at 100
RETRIES = 4

# name -> (hf dataset, config, split, question field, answer field)
SOURCES = {
    "math500": ("HuggingFaceH4/MATH-500", "default", "test", "problem", "answer"),
    "gsm8k":   ("openai/gsm8k", "main", "test", "question", "answer"),
    "hmmt25":  ("MathArena/hmmt_feb_2025", "default", "train", "problem", "answer"),
}


def fetch_rows(dataset, config, split, offset, length):
    url = ("https://datasets-server.huggingface.co/rows"
           f"?dataset={urllib.parse.quote(dataset)}&config={config}"
           f"&split={split}&offset={offset}&length={length}")
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if attempt == RETRIES - 1:
                raise
            print(f"  retry {attempt + 1}/{RETRIES - 1} after {type(e).__name__}")
            time.sleep(2 * (attempt + 1))


def clean_answer(name, raw):
    """GSM8K ships the full worked solution; the graded answer is after '####'."""
    if name == "gsm8k":
        raw = raw.split("####")[-1]
    return str(raw).strip().replace(",", "") if name == "gsm8k" else str(raw).strip()


def build(name):
    dataset, config, split, q_field, a_field = SOURCES[name]
    total = fetch_rows(dataset, config, split, 0, 1)["num_rows_total"]
    print(f"{name}: {total} rows from {dataset} [{config}/{split}]")

    out = []
    for offset in range(0, total, PAGE):
        page = fetch_rows(dataset, config, split, offset, min(PAGE, total - offset))
        for row in page["rows"]:
            r = row["row"]
            out.append({"question": r[q_field].strip(),
                        "answer": clean_answer(name, r[a_field])})
        print(f"  {len(out)}/{total}")

    path = os.path.join(HERE, f"{name}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  wrote {path} ({len(out)} questions)\n")


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SOURCES)
    for n in wanted:
        if n not in SOURCES:
            raise SystemExit(f"unknown benchmark {n!r} — pick from {list(SOURCES)}")
        build(n)
