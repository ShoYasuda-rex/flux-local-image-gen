"""BatchStatus Pydanticモデルのバリデーションテスト。
レスポンスモデルのフィールド・デフォルト値・型を検証する。
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_server import BatchStatus


class TestBatchStatusDefaults:
    """BatchStatusのデフォルト値の検証"""

    def test_minimal_batch_status(self):
        # 必須フィールドのみでインスタンス生成できる
        status = BatchStatus(
            job_id="abc123",
            status="pending",
            total=5,
            completed=0,
            results=[],
        )
        assert status.job_id == "abc123"
        assert status.status == "pending"
        assert status.total == 5
        assert status.completed == 0
        assert status.results == []
        assert status.error is None

    def test_error_is_optional(self):
        # errorフィールドはオプションでNoneがデフォルト
        status = BatchStatus(
            job_id="x",
            status="completed",
            total=1,
            completed=1,
            results=[{"index": 0}],
        )
        assert status.error is None

    def test_error_can_be_set(self):
        # errorフィールドに値を設定できる
        status = BatchStatus(
            job_id="x",
            status="failed",
            total=1,
            completed=0,
            results=[],
            error="Pipeline crashed",
        )
        assert status.error == "Pipeline crashed"


class TestBatchStatusValidation:
    """BatchStatusのバリデーションの検証"""

    def test_job_id_required(self):
        # job_idが未指定の場合はバリデーションエラー
        with pytest.raises(ValidationError):
            BatchStatus(
                status="pending",
                total=1,
                completed=0,
                results=[],
            )

    def test_status_required(self):
        # statusが未指定の場合はバリデーションエラー
        with pytest.raises(ValidationError):
            BatchStatus(
                job_id="x",
                total=1,
                completed=0,
                results=[],
            )

    def test_total_required(self):
        # totalが未指定の場合はバリデーションエラー
        with pytest.raises(ValidationError):
            BatchStatus(
                job_id="x",
                status="pending",
                completed=0,
                results=[],
            )

    def test_results_accepts_list_of_dicts(self):
        # resultsがdict要素のリストを受け入れる
        status = BatchStatus(
            job_id="x",
            status="completed",
            total=2,
            completed=2,
            results=[
                {"index": 0, "filename": "a.png"},
                {"index": 1, "filename": "b.png"},
            ],
        )
        assert len(status.results) == 2

    def test_status_accepts_all_valid_values(self):
        # 各ステータス文字列が受け入れられる（型はstrなのでバリデーションではなく慣習の確認）
        for s in ["pending", "running", "completed", "failed"]:
            status = BatchStatus(
                job_id="x",
                status=s,
                total=1,
                completed=0,
                results=[],
            )
            assert status.status == s
