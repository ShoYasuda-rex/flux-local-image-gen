"""APIエンドポイントのインテグレーションテスト。
パイプライン（GPU推論）をモック化し、全エンドポイントの動作を検証する。
副作用のある外部通信は一切発生しない。
"""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# パイプラインのロードをモック化してからインポートする
# optimum.intel は環境に依存するため、モジュール自体をモックする
mock_ov_module = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.intel"] = mock_ov_module

import api_server
from api_server import app, batch_jobs

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """各テスト前にグローバル状態をリセットし、出力先をtmpに変更する。"""
    # batch_jobs をクリア
    batch_jobs.clear()

    # OUTPUT_DIR を一時ディレクトリに差し替え
    original_output_dir = api_server.OUTPUT_DIR
    api_server.OUTPUT_DIR = tmp_path

    yield tmp_path

    # 復元
    api_server.OUTPUT_DIR = original_output_dir
    batch_jobs.clear()


@pytest.fixture
def mock_pipeline():
    """パイプラインをモック化し、ダミー画像を返す。"""
    dummy_image = Image.new("RGB", (512, 512), (128, 64, 32))
    mock_pipe = MagicMock()
    mock_pipe.return_value.images = [dummy_image]

    with patch.object(api_server, "pipe", mock_pipe), \
         patch.object(api_server, "load_pipeline", return_value=mock_pipe):
        yield mock_pipe


@pytest.fixture
def client():
    """FastAPI TestClient を生成する。lifespanイベントは無効化する。"""
    # lifespanでパイプラインロードが走るのを防ぐ
    with patch.object(api_server, "load_pipeline"):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ==================== GET /health ====================

class TestHealthEndpoint:
    """GET /health エンドポイントの検証"""

    def test_health_returns_ok(self, client):
        # ヘルスチェックが正常応答する
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_includes_model_status(self, client):
        # レスポンスにmodel_loaded フィールドが含まれる
        resp = client.get("/health")
        data = resp.json()
        assert "model_loaded" in data
        assert "model_path" in data


# ==================== POST /generate ====================

class TestGenerateEndpoint:
    """POST /generate エンドポイントの検証"""

    def test_generate_success(self, client, mock_pipeline, reset_state):
        # 正常な生成リクエストが成功する
        resp = client.post("/generate", json={
            "prompt": "a test robot",
            "num_inference_steps": 4,
            "height": 512,
            "width": 512,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "filename" in data
        assert data["filename"].endswith(".png")
        assert "generation_time_seconds" in data
        assert data["prompt"] == "a test robot"

    def test_generate_with_custom_filename(self, client, mock_pipeline, reset_state):
        # カスタムファイル名が反映される
        resp = client.post("/generate", json={
            "prompt": "a cat",
            "filename": "my_cat.png",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "my_cat.png"

    def test_generate_auto_appends_png(self, client, mock_pipeline, reset_state):
        # .png がついていないファイル名に自動付与される
        resp = client.post("/generate", json={
            "prompt": "a cat",
            "filename": "my_cat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "my_cat.png"

    def test_generate_with_remove_bg(self, client, mock_pipeline, reset_state):
        # remove_bg=True でリクエストが成功する
        resp = client.post("/generate", json={
            "prompt": "a sprite",
            "remove_bg": True,
        })
        assert resp.status_code == 200

    def test_generate_missing_prompt_returns_422(self, client):
        # promptが未指定の場合は422バリデーションエラー
        resp = client.post("/generate", json={})
        assert resp.status_code == 422

    def test_generate_invalid_steps_returns_422(self, client):
        # num_inference_stepsが範囲外の場合は422
        resp = client.post("/generate", json={
            "prompt": "test",
            "num_inference_steps": 0,
        })
        assert resp.status_code == 422

    def test_generate_invalid_height_returns_422(self, client):
        # heightが範囲外の場合は422
        resp = client.post("/generate", json={
            "prompt": "test",
            "height": 128,
        })
        assert resp.status_code == 422


# ==================== POST /batch ====================

class TestBatchEndpoint:
    """POST /batch エンドポイントの検証"""

    def test_batch_returns_job_id(self, client, mock_pipeline, reset_state):
        # バッチリクエストがjob_idを返す
        resp = client.post("/batch", json={
            "prompts": [
                {"prompt": "a cat"},
                {"prompt": "a dog"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["total"] == 2

    def test_batch_empty_prompts_returns_400(self, client):
        # 空のpromptsリストは400エラー
        resp = client.post("/batch", json={"prompts": []})
        assert resp.status_code == 400
        assert "No prompts" in resp.json()["detail"]

    def test_batch_invalid_output_dir_returns_400(self, client, reset_state):
        # output_dirがoutputs/外の場合は400エラー
        resp = client.post("/batch", json={
            "prompts": [{"prompt": "test"}],
            "output_dir": "/tmp/evil_dir",
        })
        assert resp.status_code == 400
        assert "output_dir" in resp.json()["detail"]


# ==================== GET /batch/{job_id} ====================

class TestBatchStatusEndpoint:
    """GET /batch/{job_id} エンドポイントの検証"""

    def test_batch_status_not_found(self, client):
        # 存在しないjob_idは404
        resp = client.get("/batch/nonexistent_id")
        assert resp.status_code == 404

    def test_batch_status_returns_job_info(self, client):
        # 登録済みジョブの情報が返る
        batch_jobs["test123"] = {
            "job_id": "test123",
            "status": "running",
            "total": 3,
            "completed": 1,
            "results": [{"index": 0, "filename": "test.png"}],
        }
        resp = client.get("/batch/test123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test123"
        assert data["status"] == "running"
        assert data["completed"] == 1


# ==================== GET /outputs/{filename} ====================

class TestOutputsEndpoint:
    """GET /outputs/{filename} エンドポイントの検証"""

    def test_output_file_not_found(self, client, reset_state):
        # 存在しないファイルは404
        resp = client.get("/outputs/nonexistent.png")
        assert resp.status_code == 404

    def test_output_file_exists(self, client, reset_state):
        # 存在するファイルが返却される
        tmp_dir = reset_state
        test_file = tmp_dir / "test_image.png"
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        img.save(str(test_file))

        # OUTPUT_DIRがtmp_dirになっているのでパストラバーサルチェックを通る
        resp = client.get("/outputs/test_image.png")
        assert resp.status_code == 200

    def test_path_traversal_blocked(self, client, reset_state):
        # パストラバーサル攻撃がブロックされる
        resp = client.get("/outputs/../api_server.py")
        assert resp.status_code in (400, 404)


# ==================== generate_single / run_batch ロジック ====================

class TestGenerateSingleLogic:
    """generate_single関数のロジック検証"""

    def test_filename_auto_generated_from_prompt(self, mock_pipeline, reset_state):
        # filenameが未指定の場合、プロンプトからスラッグが生成される
        from api_server import generate_single, GenerateRequest

        req = GenerateRequest(prompt="a beautiful sunset")
        result = generate_single(req, reset_state)
        assert result["filename"].startswith("a_beautiful_sunset_")
        assert result["filename"].endswith(".png")

    def test_result_contains_expected_fields(self, mock_pipeline, reset_state):
        # 戻り値に必要なフィールドが含まれる
        from api_server import generate_single, GenerateRequest

        req = GenerateRequest(prompt="test prompt")
        result = generate_single(req, reset_state)
        assert "filename" in result
        assert "path" in result
        assert "prompt" in result
        assert "generation_time_seconds" in result
        assert "dimensions" in result
        assert "steps" in result


class TestRunBatchLogic:
    """run_batch関数のロジック検証"""

    def test_batch_completes_all_items(self, mock_pipeline, reset_state):
        # バッチ内の全アイテムが処理される
        from api_server import run_batch, GenerateRequest

        job_id = "test_batch_001"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 2,
            "completed": 0,
            "results": [],
        }
        requests = [
            GenerateRequest(prompt="item1"),
            GenerateRequest(prompt="item2"),
        ]
        run_batch(job_id, requests, reset_state)

        assert batch_jobs[job_id]["status"] == "completed"
        assert batch_jobs[job_id]["completed"] == 2
        assert len(batch_jobs[job_id]["results"]) == 2

    def test_batch_handles_individual_failure(self, reset_state):
        # 個別アイテムの失敗がバッチ全体を止めない
        from api_server import run_batch, GenerateRequest

        job_id = "test_batch_fail"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 2,
            "completed": 0,
            "results": [],
        }

        # generate_singleが1回目で例外、2回目で成功するようモック
        dummy_image = Image.new("RGB", (512, 512), (128, 64, 32))
        mock_pipe = MagicMock()
        mock_pipe.return_value.images = [dummy_image]

        call_count = 0

        def mock_generate_single(req, output_dir):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("GPU error")
            return {
                "filename": "ok.png",
                "path": str(output_dir / "ok.png"),
                "prompt": req.prompt,
                "generation_time_seconds": 1.0,
                "dimensions": "512x512",
                "steps": 4,
            }

        requests = [
            GenerateRequest(prompt="will_fail"),
            GenerateRequest(prompt="will_succeed"),
        ]

        with patch("api_server.generate_single", side_effect=mock_generate_single):
            run_batch(job_id, requests, reset_state)

        assert batch_jobs[job_id]["status"] == "completed"
        assert batch_jobs[job_id]["completed"] == 2
        # 1つ目はエラー
        assert "error" in batch_jobs[job_id]["results"][0]
        # 2つ目は成功
        assert "filename" in batch_jobs[job_id]["results"][1]

    def test_batch_writes_manifest_json(self, mock_pipeline, reset_state):
        # バッチ完了後にmanifest JSONが出力される
        from api_server import run_batch, GenerateRequest

        job_id = "test_manifest"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        requests = [GenerateRequest(prompt="test")]
        run_batch(job_id, requests, reset_state)

        manifest_path = reset_state / f"batch_{job_id}.json"
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["status"] == "completed"
