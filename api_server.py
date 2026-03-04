"""
FLUX.1 OpenVINO 画像生成 API サーバー
起動:
  .\venv\Scripts\Activate.ps1
  python api_server.py

API エンドポイント:
  POST /generate       — 1枚生成（同期）
  POST /batch          — バッチ生成（非同期、ジョブID返却）
  GET  /batch/{job_id} — バッチジョブ状態確認
  GET  /health         — ヘルスチェック
"""
import os
import sys
import time
import uuid
import json
import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from typing import Optional

os.environ["PYTHONIOENCODING"] = "utf-8"

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

MODEL_PATH = Path(__file__).parent / "models" / "flux1-schnell-int8"
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

pipe = None
pipe_lock = threading.Lock()
batch_jobs: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=load_pipeline, daemon=True).start()
    yield


app = FastAPI(title="FLUX.1 OpenVINO Generator", version="1.0.0", lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str
    num_inference_steps: int = Field(default=4, ge=1, le=50)
    height: int = Field(default=512, ge=256, le=1024)
    width: int = Field(default=512, ge=256, le=1024)
    filename: Optional[str] = None


class BatchRequest(BaseModel):
    prompts: list[GenerateRequest]
    output_dir: Optional[str] = None


class BatchStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    total: int
    completed: int
    results: list[dict]
    error: Optional[str] = None


def load_pipeline():
    global pipe
    if pipe is not None:
        return pipe

    with pipe_lock:
        if pipe is not None:
            return pipe

        print(f"Loading pipeline from {MODEL_PATH}...")
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

        print(f"Pipeline loaded in {time.time() - t0:.1f}s")
        return pipe


def generate_single(req: GenerateRequest, output_dir: Path) -> dict:
    pipeline = load_pipeline()

    filename = req.filename or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    filename = Path(filename).name
    if not filename.endswith(".png"):
        filename += ".png"

    output_path = output_dir / filename

    t0 = time.time()
    with pipe_lock:
        image = pipeline(
            prompt=req.prompt,
            num_inference_steps=req.num_inference_steps,
            height=req.height,
            width=req.width,
            guidance_scale=0.0,
        ).images[0]

    image.save(str(output_path))
    gen_time = time.time() - t0

    return {
        "filename": filename,
        "path": str(output_path),
        "prompt": req.prompt,
        "generation_time_seconds": round(gen_time, 1),
        "dimensions": f"{req.width}x{req.height}",
        "steps": req.num_inference_steps,
    }


def run_batch(job_id: str, requests: list[GenerateRequest], output_dir: Path):
    job = batch_jobs[job_id]
    job["status"] = "running"

    for i, req in enumerate(requests):
        try:
            result = generate_single(req, output_dir)
            result["index"] = i
            job["results"].append(result)
            job["completed"] = i + 1
        except Exception as e:
            job["results"].append({
                "index": i,
                "error": str(e),
                "prompt": req.prompt,
            })
            job["completed"] = i + 1

    job["status"] = "completed"
    job["finished_at"] = datetime.now().isoformat()

    manifest_path = output_dir / f"batch_{job_id}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": pipe is not None,
        "model_path": str(MODEL_PATH),
        "gpu_available": True,
    }


@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        result = await asyncio.to_thread(generate_single, req, OUTPUT_DIR)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch")
async def batch_generate(req: BatchRequest):
    if not req.prompts:
        raise HTTPException(status_code=400, detail="No prompts provided")

    job_id = uuid.uuid4().hex[:12]
    if req.output_dir:
        output_dir = Path(req.output_dir).resolve()
        if not str(output_dir).startswith(str(OUTPUT_DIR.resolve())):
            raise HTTPException(status_code=400, detail="output_dir must be within outputs/")
    else:
        output_dir = OUTPUT_DIR / f"batch_{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "total": len(req.prompts),
        "completed": 0,
        "results": [],
        "output_dir": str(output_dir),
        "started_at": datetime.now().isoformat(),
    }

    thread = threading.Thread(
        target=run_batch,
        args=(job_id, req.prompts, output_dir),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "total": len(req.prompts), "output_dir": str(output_dir)}


@app.get("/batch/{job_id}")
async def batch_status(job_id: str):
    if job_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return batch_jobs[job_id]


@app.get("/outputs/{filename}")
async def get_output(filename: str):
    path = (OUTPUT_DIR / filename).resolve()
    if not str(path).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="image/png")


if __name__ == "__main__":
    print("=" * 60)
    print("FLUX.1 OpenVINO Generator API")
    print(f"Model: {MODEL_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8188, log_level="info")
