"""完了済みバッチジョブの自動削除ロジックのテスト。
変更: run_batch完了後、completed状態のジョブがBATCH_JOBS_MAX_COMPLETED(100)を
超えた場合、finished_atが古いものから削除する機能が追加された。
"""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# optimum.intel をモック化してからインポート
mock_ov_module = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.intel"] = mock_ov_module

import api_server
from api_server import run_batch, GenerateRequest, batch_jobs, BATCH_JOBS_MAX_COMPLETED


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """各テスト前にグローバル状態をリセットし、出力先をtmpに変更する。"""
    batch_jobs.clear()
    original_output_dir = api_server.OUTPUT_DIR
    api_server.OUTPUT_DIR = tmp_path
    yield tmp_path
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


class TestBatchJobsCleanup:
    """完了済みジョブの自動削除ロジックの検証"""

    def test_max_completed_constant_is_100(self):
        # BATCH_JOBS_MAX_COMPLETED定数が100であること
        assert BATCH_JOBS_MAX_COMPLETED == 100

    def test_no_cleanup_when_under_limit(self, mock_pipeline, reset_state):
        # 完了済みジョブが上限以下なら削除されない
        # 事前に99件の完了済みジョブを登録
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(99):
            batch_jobs[f"old_{i}"] = {
                "job_id": f"old_{i}",
                "status": "completed",
                "finished_at": (base_time + timedelta(minutes=i)).isoformat(),
            }

        # 新しいジョブを実行（これで100件になる）
        job_id = "new_job"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        run_batch(job_id, [GenerateRequest(prompt="test")], reset_state)

        # 100件ちょうどなので削除されない
        completed_count = sum(1 for v in batch_jobs.values() if v.get("status") == "completed")
        assert completed_count == 100

    def test_cleanup_removes_oldest_when_over_limit(self, mock_pipeline, reset_state):
        # 完了済みジョブが上限を超えたら最も古いものが削除される
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(100):
            batch_jobs[f"old_{i}"] = {
                "job_id": f"old_{i}",
                "status": "completed",
                "finished_at": (base_time + timedelta(minutes=i)).isoformat(),
            }

        # 新しいジョブを実行（101件目、上限超過）
        job_id = "new_job"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        run_batch(job_id, [GenerateRequest(prompt="test")], reset_state)

        # 最も古いold_0が削除されている
        assert "old_0" not in batch_jobs
        # 新しいジョブは残っている
        assert job_id in batch_jobs
        # 完了済みジョブが上限以下になっている
        completed_count = sum(1 for v in batch_jobs.values() if v.get("status") == "completed")
        assert completed_count == 100

    def test_cleanup_preserves_running_jobs(self, mock_pipeline, reset_state):
        # running状態のジョブは削除対象にならない
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(100):
            batch_jobs[f"old_{i}"] = {
                "job_id": f"old_{i}",
                "status": "completed",
                "finished_at": (base_time + timedelta(minutes=i)).isoformat(),
            }
        # running状態のジョブを追加
        batch_jobs["running_job"] = {
            "job_id": "running_job",
            "status": "running",
            "total": 5,
            "completed": 2,
            "results": [],
        }

        # 新しいジョブを実行（completed 101件、running 1件）
        job_id = "new_job"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        run_batch(job_id, [GenerateRequest(prompt="test")], reset_state)

        # running状態のジョブは残っている
        assert "running_job" in batch_jobs
        assert batch_jobs["running_job"]["status"] == "running"

    def test_cleanup_removes_correct_number(self, mock_pipeline, reset_state):
        # 上限を大きく超えた場合、正しい数だけ削除される
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(103):
            batch_jobs[f"old_{i}"] = {
                "job_id": f"old_{i}",
                "status": "completed",
                "finished_at": (base_time + timedelta(minutes=i)).isoformat(),
            }

        # 新しいジョブを実行（104件目）
        job_id = "new_job"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        run_batch(job_id, [GenerateRequest(prompt="test")], reset_state)

        # 4件削除されて100件になっている
        completed_count = sum(1 for v in batch_jobs.values() if v.get("status") == "completed")
        assert completed_count == 100
        # 最も古い4件が削除されている
        assert "old_0" not in batch_jobs
        assert "old_1" not in batch_jobs
        assert "old_2" not in batch_jobs
        assert "old_3" not in batch_jobs
        # 5件目以降は残っている
        assert "old_4" in batch_jobs

    def test_cleanup_sorts_by_finished_at(self, mock_pipeline, reset_state):
        # finished_atの古い順に削除される（IDの順ではない）
        base_time = datetime(2026, 1, 1, 0, 0, 0)
        for i in range(100):
            batch_jobs[f"job_{i}"] = {
                "job_id": f"job_{i}",
                "status": "completed",
                # 意図的にID順とfinished_at順を逆にする
                "finished_at": (base_time + timedelta(minutes=99 - i)).isoformat(),
            }

        # 新しいジョブを実行（101件目）
        job_id = "new_job"
        batch_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "total": 1,
            "completed": 0,
            "results": [],
        }
        run_batch(job_id, [GenerateRequest(prompt="test")], reset_state)

        # job_99が最もfinished_atが古い（minutes=0）ので削除される
        assert "job_99" not in batch_jobs
        # job_0が最もfinished_atが新しい（minutes=99）ので残る
        assert "job_0" in batch_jobs
