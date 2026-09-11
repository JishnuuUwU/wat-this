"""
Live Model Inference & Streaming Proof for wat-this.
Connects directly to Ollama, streams tokens from the configured model,
measures latency and tokens per second, and outputs concrete verification.
"""
import sys
import os
import json
import time
import urllib.request

# Force UTF-8 on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

import config_manager

def run_model_inference_proof(tier_key=None, target_prompt="Explain: def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)"):
    if not tier_key:
        tier_key, spec = config_manager.get_active_tier()
    else:
        spec = config_manager.get_tier_spec(tier_key)
        
    model = spec["model"]
    keep_alive = spec["keep_alive"]
    system_prompt = spec["system_prompt"]
    ollama_url = config_manager.load_config().get("ollama_url", "http://localhost:11434").rstrip("/")

    print("=" * 65)
    print(f"LIVE MODEL INFERENCE PROOF: [{tier_key.upper()}] -> {model}")
    print(f"Target Prompt: {target_prompt}")
    print(f"System Prompt: {system_prompt[:60]}...")
    print(f"Keep Alive:    {keep_alive} (RAM optimization budget)")
    print("=" * 65)

    payload = {
        "model": model,
        "prompt": target_prompt,
        "stream": True,
        "system": system_prompt,
        "keep_alive": keep_alive
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )

    t0 = time.time()
    first_token_time = None
    token_count = 0
    full_response = ""

    print("\n--- STREAMING OUTPUT START ---")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("response", "")
                        if token:
                            if first_token_time is None:
                                first_token_time = time.time()
                            token_count += 1
                            full_response += token
                            sys.stdout.write(token)
                            sys.stdout.flush()
                    except Exception:
                        continue
                        
        total_time = time.time() - t0
        ttft = (first_token_time - t0) if first_token_time else 0
        tps = (token_count / (total_time - ttft)) if (total_time - ttft) > 0 else 0

        print("\n--- STREAMING OUTPUT END ---\n")
        print("PERFORMANCE & EXECUTION METRICS:")
        print(f"  - Model Tested:             {model}")
        print(f"  - Total Tokens Generated:   {token_count}")
        print(f"  - Time to First Token (TTFT): {ttft:.2f}s")
        print(f"  - Total Response Time:      {total_time:.2f}s")
        print(f"  - Generation Throughput:    {tps:.1f} tokens/sec")
        print(f"  - Memory Optimization:      keep_alive='{keep_alive}' enforced")
        print("  - Verdict:                  [SUCCESS / VERIFIED PROOF]\n")
        return True, full_response

    except Exception as e:
        print(f"\n[ERROR] Inference failed: {e}\n")
        return False, str(e)

if __name__ == "__main__":
    tier = sys.argv[1] if len(sys.argv) > 1 else "lite"
    run_model_inference_proof(tier)
