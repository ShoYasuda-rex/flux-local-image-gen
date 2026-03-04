"""4ステップ vs 8ステップ 品質比較テスト"""
import os
import time
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

MODEL_PATH = Path(__file__).parent / "models" / "flux1-schnell-int8"
OUTPUT_DIR = Path(__file__).parent / "outputs" / "steps_compare"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading pipeline...")
t0 = time.time()

from optimum.intel import OVFluxPipeline

cache_dir = str(MODEL_PATH / "model_cache")
os.makedirs(cache_dir, exist_ok=True)

pipe = OVFluxPipeline.from_pretrained(
    str(MODEL_PATH),
    device="GPU",
    ov_config={
        "PERFORMANCE_HINT": "LATENCY",
        "CACHE_DIR": cache_dir,
    },
)
print(f"Pipeline loaded in {time.time() - t0:.1f}s\n")

prompt = "pixel art style, RPG warrior man, heavy armor, sword and shield, Final Fantasy style, full body, game character sprite, clean pixel art"

for steps in [4, 8]:
    print(f"Generating {steps} steps...")
    t0 = time.time()
    image = pipe(
        prompt=prompt,
        num_inference_steps=steps,
        height=512,
        width=512,
        guidance_scale=0.0,
    ).images[0]
    gen_time = time.time() - t0

    filename = f"warrior_{steps}steps.png"
    image.save(str(OUTPUT_DIR / filename))
    print(f"  {filename} — {gen_time:.1f}s\n")

print(f"Done! Compare images in {OUTPUT_DIR}")
