"""バッチ生成 API テスト"""
import urllib.request
import json
import time
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

API_URL = "http://127.0.0.1:8188"

payload = json.dumps({
    "prompts": [
        {"prompt": "pixel art style, a green slime monster, 32x32 sprite, game enemy", "filename": "slime.png", "num_inference_steps": 4, "height": 512, "width": 512},
        {"prompt": "pixel art style, a wooden sword, 32x32 sprite, game item", "filename": "sword.png", "num_inference_steps": 4, "height": 512, "width": 512},
        {"prompt": "pixel art style, a red potion bottle, 32x32 sprite, game item", "filename": "potion.png", "num_inference_steps": 4, "height": 512, "width": 512},
    ]
}).encode()

req = urllib.request.Request(
    f"{API_URL}/batch",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read().decode())
job_id = result["job_id"]
total = result["total"]
print(f"Batch job started: {job_id}")
print(f"Total prompts: {total}")

while True:
    time.sleep(10)
    status_req = urllib.request.Request(f"{API_URL}/batch/{job_id}")
    status_resp = urllib.request.urlopen(status_req, timeout=10)
    status = json.loads(status_resp.read().decode())
    completed = status["completed"]
    print(f"  Status: {status['status']} ({completed}/{total})")

    if status["status"] in ("completed", "failed"):
        print()
        for r in status["results"]:
            if "error" in r:
                print(f"  [{r['index']}] ERROR: {r['error']}")
            else:
                print(f"  [{r['index']}] {r['filename']} ({r['generation_time_seconds']}s)")
        break

print("Done!")
