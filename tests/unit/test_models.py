"""Pydanticモデル（GenerateRequest, BatchRequest）のバリデーションテスト。
リクエストパラメータの型・範囲・デフォルト値が正しいことを検証する。
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_server import GenerateRequest, BatchRequest


class TestGenerateRequestDefaults:
    """GenerateRequestのデフォルト値の検証"""

    def test_minimal_request_has_defaults(self):
        # promptのみ指定で他はデフォルト値が設定される
        req = GenerateRequest(prompt="a cat")
        assert req.num_inference_steps == 4
        assert req.height == 512
        assert req.width == 512
        assert req.filename is None
        assert req.remove_bg is False

    def test_all_fields_specified(self):
        # 全フィールドを明示的に指定できる
        req = GenerateRequest(
            prompt="a dog",
            num_inference_steps=8,
            height=256,
            width=1024,
            filename="test.png",
            remove_bg=True,
        )
        assert req.prompt == "a dog"
        assert req.num_inference_steps == 8
        assert req.height == 256
        assert req.width == 1024
        assert req.filename == "test.png"
        assert req.remove_bg is True


class TestGenerateRequestValidation:
    """GenerateRequestのバリデーションの検証"""

    def test_prompt_required(self):
        # promptが未指定の場合はバリデーションエラー
        with pytest.raises(ValidationError):
            GenerateRequest()

    def test_steps_minimum_is_1(self):
        # num_inference_stepsの最小値は1
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", num_inference_steps=0)

    def test_steps_maximum_is_50(self):
        # num_inference_stepsの最大値は50
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", num_inference_steps=51)

    def test_height_minimum_is_256(self):
        # heightの最小値は256
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", height=128)

    def test_height_maximum_is_1024(self):
        # heightの最大値は1024
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", height=2048)

    def test_width_minimum_is_256(self):
        # widthの最小値は256
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", width=128)

    def test_width_maximum_is_1024(self):
        # widthの最大値は1024
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="test", width=2048)

    def test_boundary_values_accepted(self):
        # 境界値が受け入れられる
        req = GenerateRequest(
            prompt="test",
            num_inference_steps=1,
            height=256,
            width=256,
        )
        assert req.num_inference_steps == 1
        assert req.height == 256

        req2 = GenerateRequest(
            prompt="test",
            num_inference_steps=50,
            height=1024,
            width=1024,
        )
        assert req2.num_inference_steps == 50
        assert req2.height == 1024


class TestBatchRequest:
    """BatchRequestの検証"""

    def test_minimal_batch_request(self):
        # プロンプト1つのバッチリクエスト
        req = BatchRequest(prompts=[GenerateRequest(prompt="a cat")])
        assert len(req.prompts) == 1
        assert req.output_dir is None

    def test_multiple_prompts(self):
        # 複数プロンプトのバッチリクエスト
        req = BatchRequest(
            prompts=[
                GenerateRequest(prompt="a cat"),
                GenerateRequest(prompt="a dog"),
            ]
        )
        assert len(req.prompts) == 2

    def test_output_dir_optional(self):
        # output_dirはオプション
        req = BatchRequest(
            prompts=[GenerateRequest(prompt="test")],
            output_dir="/some/path",
        )
        assert req.output_dir == "/some/path"

    def test_empty_prompts_accepted_by_model(self):
        # Pydanticモデル自体は空リストを許可する（APIレベルで400を返す）
        req = BatchRequest(prompts=[])
        assert len(req.prompts) == 0
