"""DeepConf-LOW baseline on Modal: the July v4 belt's repo-exact deepconf arm
(16-trace warmup -> frozen bar -> instant cuts) + the paper's consensus
stopping (tau=0.95) that facebookresearch/deepconf never shipped.

Run:    modal run --detach modal_deepconf.py --qid 6 --model deepseek-ai/DeepSeek-R1-0528-Qwen3-8B
Fetch:  modal volume ls peerconf-out
"""
import os
import re
from pathlib import Path

import modal

HERE = Path(__file__).parent

app = modal.App("peerconf-deepconf-low")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("vllm==0.10.2", "transformers==4.56.2", "numpy", "requests")
    .pip_install(
        "git+https://github.com/facebookresearch/deepconf.git",
        "git+https://github.com/hao-ai-lab/Dynasor.git",
    )
    .add_local_file(HERE / "cell2_deepconf.py", "/root/cell2-stopped.py")
    .add_local_file(HERE.parent / "benchmarks" / "aime25.jsonl", "/root/aime25.jsonl")
)

hf_cache = modal.Volume.from_name("peerconf-hf-cache", create_if_missing=True)
out_vol = modal.Volume.from_name("peerconf-out", create_if_missing=True)


def _boot_server(model: str):
    import subprocess
    import time

    import requests

    server = subprocess.Popen(
        ["vllm", "serve", model,
         "--port", "8000",
         "--max-model-len", "32768",
         "--gpu-memory-utilization", "0.92",
         "--max-logprobs", "20"],
        stdout=open("vllm_server.log", "w"), stderr=subprocess.STDOUT)
    t0 = time.time()
    while True:
        try:
            if requests.get("http://localhost:8000/health", timeout=5).status_code == 200:
                print(f"Server up after {time.time() - t0:.0f}s")
                return server
        except requests.exceptions.RequestException:
            pass
        if server.poll() is not None:
            print(open("vllm_server.log").read()[-8000:])
            raise RuntimeError("Server died — log tail above")
        if time.time() - t0 > 1500:
            raise RuntimeError("Server not up after 25 min")
        time.sleep(5)


@app.function(
    image=image,
    gpu="A100",          # 16 seats — the July config, fits 40GB fine
    timeout=20 * 60 * 60,
    volumes={"/root/.cache/huggingface": hf_cache, "/out": out_vol},
)
def run_deepconf(qid: int, model: str, percentile: int):
    import time

    os.chdir("/root")
    os.environ["OUT_DIR"] = "/out"
    os.environ["ARM"] = "deepconf"          # frozen warmup bar + consensus stop
    os.environ["LINE_MODE"] = "percentile"

    src = Path("cell2-stopped.py").read_text()
    src = re.sub(r"^QID\s*=\s*\d+", f"QID            = {qid}", src, count=1, flags=re.M)
    src = re.sub(r'^MODEL   = ".*"', f'MODEL   = "{model}"', src, count=1, flags=re.M)
    src = re.sub(r"^CONFIDENCE_PERCENTILE = \d+",
                 f"CONFIDENCE_PERCENTILE = {percentile}", src, count=1, flags=re.M)

    server = _boot_server(model)
    t0 = time.time()
    try:
        exec(compile(src, "cell2-stopped.py", "exec"), {"__name__": "__main__"})
    finally:
        server.terminate()
        out_vol.commit()
    print(f"\nDeepConf-low run over: {(time.time() - t0) / 60:.0f} min")


@app.local_entrypoint()
def main(qid: int = 6, model: str = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
         percentile: int = 10):
    run_deepconf.remote(qid, model, percentile)
