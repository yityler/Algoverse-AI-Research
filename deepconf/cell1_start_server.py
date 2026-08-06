# ======================= CELL 1 — START THE SERVER (run once) =======================
# If another model is loaded on this GPU, free it first.
import subprocess, time, requests, os

OUT_DIR = os.environ.get("OUT_DIR", "peerconf_out")   # CELL 2's save block writes here
os.makedirs(OUT_DIR, exist_ok=True)

MODEL  = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
SERVER = "http://localhost:8000"

# stock vLLM server — PeerConf judges on the client side, no custom logits processor
server_proc = subprocess.Popen(
    ["vllm", "serve", MODEL,
     "--port", "8000",
     "--max-model-len", "32768",
     "--gpu-memory-utilization", "0.92",
     "--max-logprobs", "20"],
    stdout=open("vllm_server.log", "w"), stderr=subprocess.STDOUT)
print("Server starting (model load takes a few minutes)... tail vllm_server.log if curious")

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
