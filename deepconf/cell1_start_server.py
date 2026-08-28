# ======================= CELL 1 — START THE SERVER (run once) =======================
# Stock vLLM server. CELL 2 streams tokens over HTTP and judges the confidence
# window client-side, so no logits processor is loaded here.
import subprocess, time, requests, os

OUT_DIR = os.environ.get("OUT_DIR", "deepconf_out")   # CELL 2's save block writes here
os.makedirs(OUT_DIR, exist_ok=True)

MODEL  = os.environ.get("MODEL", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")
SERVER = "http://localhost:8000"

# Shard over every GPU this box exposes. TP=<n> overrides.
try:
    import torch
    _gpus = torch.cuda.device_count()
except Exception:
    _gpus = 0
TP = int(os.environ.get("TP", 0)) or _gpus or 1

server_proc = subprocess.Popen(
    ["vllm", "serve", MODEL,
     "--port", "8000",
     "--max-model-len", "65536",
     "--tensor-parallel-size", str(TP),
     "--gpu-memory-utilization", "0.92",
     "--max-logprobs", "20"],
    stdout=open("vllm_server.log", "w"), stderr=subprocess.STDOUT)
print(f"Server starting on {TP} GPU(s) (model load takes a few minutes)... "
      "tail vllm_server.log if curious")

t0 = time.time()
while True:
    try:
        if requests.get(f"{SERVER}/health", timeout=5).status_code == 200:
            print(f"Server up after {time.time()-t0:.0f}s"); break
    except requests.exceptions.RequestException:
        pass
    if server_proc.poll() is not None:
        raise RuntimeError("Server died — read vllm_server.log")
    if time.time() - t0 > 1200:
        raise RuntimeError("Server not up after 20 min — read vllm_server.log")
    time.sleep(5)
