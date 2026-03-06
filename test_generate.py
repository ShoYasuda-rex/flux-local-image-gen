"""
Step 4: FLUX.1-schnell 単体テスト（1枚生成）
venv を有効化して実行:
  .\venv\Scripts\Activate.ps1
  python test_generate.py
"""
import os
import sys
import time
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

MODEL_PATH = Path(__file__).parent / "models" / "flux1-schnell-int8"

if not MODEL_PATH.exists():
    print(f"Model not found at {MODEL_PATH}")
    print("Run: huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8")
    sys.exit(1)

transformer_bin = MODEL_PATH / "transformer" / "openvino_model.bin"
if not transformer_bin.exists() or transformer_bin.stat().st_size < 1_000_000:
    print(f"transformer/openvino_model.bin missing or too small ({transformer_bin.stat().st_size if transformer_bin.exists() else 0} bytes)")
    print("Model download may be incomplete. Run: huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8")
    sys.exit(1)

print(f"Model path: {MODEL_PATH}")
print(f"Transformer size: {transformer_bin.stat().st_size / (1024**3):.2f} GB")
print()

from openvino import Core
core = Core()
print(f"Available devices: {core.available_devices}")
print()

print("Loading pipeline (this may take several minutes on first run)...")
t0 = time.time()

from optimum.intel import OVFluxPipeline

pipe = OVFluxPipeline.from_pretrained(str(MODEL_PATH), device="GPU")
load_time = time.time() - t0
print(f"Pipeline loaded in {load_time:.1f}s")
print()

prompt = "pixel art style, a small robot standing in a forest, 32x32 sprite"
print(f"Generating with prompt: {prompt}")
print("num_inference_steps=4, height=512, width=512")
print()

t0 = time.time()
image = pipe(
    prompt=prompt,
    num_inference_steps=4,  # schnell is optimized for 4 steps
    height=512,
    width=512,
).images[0]
gen_time = time.time() - t0

output_path = Path(__file__).parent / "test_output.png"
image.save(str(output_path))

print(f"Generation completed in {gen_time:.1f}s")
print(f"Output saved to: {output_path}")
print("Done!")
