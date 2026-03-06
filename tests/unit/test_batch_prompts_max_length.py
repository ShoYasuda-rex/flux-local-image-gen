"""BatchRequest.prompts の max_length=20 バリデーションテスト。
変更: prompts フィールドに max_length=20 制約が追加された。
20件以下は許可、21件以上はバリデーションエラーになることを検証する。
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_server import GenerateRequest, BatchRequest


class TestBatchPromptsMaxLength:
    """BatchRequest.prompts の max_length=20 制約の検証"""

    def test_20_prompts_accepted(self):
        # 上限ちょうど20件は許可される
        prompts = [GenerateRequest(prompt=f"prompt_{i}") for i in range(20)]
        req = BatchRequest(prompts=prompts)
        assert len(req.prompts) == 20

    def test_21_prompts_rejected(self):
        # 21件はバリデーションエラーになる
        prompts = [GenerateRequest(prompt=f"prompt_{i}") for i in range(21)]
        with pytest.raises(ValidationError) as exc_info:
            BatchRequest(prompts=prompts)
        # max_length 違反のエラーであることを確認
        errors = exc_info.value.errors()
        assert any(
            e["type"] in ("too_long", "list_too_long") for e in errors
        ), f"Expected max_length error, got: {errors}"

    def test_1_prompt_accepted(self):
        # 1件は問題なく許可される
        req = BatchRequest(prompts=[GenerateRequest(prompt="single")])
        assert len(req.prompts) == 1

    def test_19_prompts_accepted(self):
        # 上限未満の19件は許可される
        prompts = [GenerateRequest(prompt=f"prompt_{i}") for i in range(19)]
        req = BatchRequest(prompts=prompts)
        assert len(req.prompts) == 19
