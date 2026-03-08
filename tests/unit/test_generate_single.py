"""generate_single 関数のユニットテスト。
ファイル名生成ロジック（サフィックス付与、拡張子除去）、remove_bg分岐、
戻り値フィールドの検証を行う。
"""
import sys
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# optimum.intel をモック化してからインポート
mock_ov_module = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.intel"] = mock_ov_module

import api_server
from api_server import generate_single, GenerateRequest


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """出力先をtmpに差し替える。"""
    original_output_dir = api_server.OUTPUT_DIR
    api_server.OUTPUT_DIR = tmp_path
    yield tmp_path
    api_server.OUTPUT_DIR = original_output_dir


@pytest.fixture
def mock_pipeline():
    """パイプラインをモック化し、ダミー画像を返す。"""
    dummy_image = Image.new("RGB", (512, 512), (128, 64, 32))
    mock_pipe = MagicMock()
    mock_pipe.return_value.images = [dummy_image]
    with patch.object(api_server, "pipe", mock_pipe), \
         patch.object(api_server, "load_pipeline", return_value=mock_pipe):
        yield mock_pipe


class TestFilenameGeneration:
    """ファイル名生成ロジックの検証（変更後: 常にサフィックス付与）"""

    def test_auto_filename_has_slug_and_suffix(self, mock_pipeline, reset_state):
        # filename未指定時、プロンプトスラッグ + 4桁hex + .png の形式になる
        req = GenerateRequest(prompt="a red dragon")
        result = generate_single(req, reset_state)
        # パターン: {slug}_{4桁hex}.png
        assert re.match(r"a_red_dragon_[0-9a-f]{4}\.png$", result["filename"])

    def test_custom_filename_gets_suffix(self, mock_pipeline, reset_state):
        # カスタムファイル名にもサフィックスが付与される
        req = GenerateRequest(prompt="a cat", filename="my_cat.png")
        result = generate_single(req, reset_state)
        # my_cat_{4桁hex}.png の形式になる（.pngは拡張子として除去され、stemがベースになる）
        assert re.match(r"my_cat_[0-9a-f]{4}\.png$", result["filename"])

    def test_custom_filename_without_extension_gets_suffix(self, mock_pipeline, reset_state):
        # 拡張子なしのカスタムファイル名にもサフィックスが付与される
        req = GenerateRequest(prompt="a cat", filename="my_cat")
        result = generate_single(req, reset_state)
        assert re.match(r"my_cat_[0-9a-f]{4}\.png$", result["filename"])

    def test_custom_filename_with_jpg_extension_becomes_png(self, mock_pipeline, reset_state):
        # .jpg拡張子が.pngに置き換えられる（stemのみ使用）
        req = GenerateRequest(prompt="a cat", filename="photo.jpg")
        result = generate_single(req, reset_state)
        assert result["filename"].endswith(".png")
        assert ".jpg" not in result["filename"]

    def test_each_generation_has_unique_suffix(self, mock_pipeline, reset_state):
        # 同じプロンプトでも毎回異なるサフィックスが生成される
        req = GenerateRequest(prompt="same prompt")
        result1 = generate_single(req, reset_state)
        result2 = generate_single(req, reset_state)
        assert result1["filename"] != result2["filename"]

    def test_output_file_actually_created(self, mock_pipeline, reset_state):
        # 生成されたファイルが実際にディスク上に存在する
        req = GenerateRequest(prompt="a test image")
        result = generate_single(req, reset_state)
        output_path = Path(result["path"])
        assert output_path.exists()


class TestRemoveBgIntegration:
    """generate_single内のremove_bg分岐の検証"""

    def test_remove_bg_false_does_not_call_remove_black_bg(self, mock_pipeline, reset_state):
        # remove_bg=Falseの場合、_remove_black_bgが呼ばれない
        req = GenerateRequest(prompt="a cat", remove_bg=False)
        with patch.object(api_server, "_remove_black_bg") as mock_remove:
            generate_single(req, reset_state)
            mock_remove.assert_not_called()

    def test_remove_bg_true_calls_remove_black_bg(self, mock_pipeline, reset_state):
        # remove_bg=Trueの場合、_remove_black_bgが呼ばれる
        req = GenerateRequest(prompt="a sprite", remove_bg=True)
        rgba_image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        with patch.object(api_server, "_remove_black_bg", return_value=rgba_image) as mock_remove:
            generate_single(req, reset_state)
            mock_remove.assert_called_once()

    def test_remove_bg_true_saves_rgba_image(self, mock_pipeline, reset_state):
        # remove_bg=Trueの場合、保存画像がRGBAモード
        req = GenerateRequest(prompt="a sprite", remove_bg=True)
        result = generate_single(req, reset_state)
        saved_image = Image.open(result["path"])
        assert saved_image.mode == "RGBA"


class TestResultFields:
    """generate_singleの戻り値フィールドの検証"""

    def test_result_prompt_matches_request(self, mock_pipeline, reset_state):
        # 戻り値のpromptがリクエストと一致する
        req = GenerateRequest(prompt="a blue sky")
        result = generate_single(req, reset_state)
        assert result["prompt"] == "a blue sky"

    def test_result_dimensions_format(self, mock_pipeline, reset_state):
        # dimensionsが "{width}x{height}" 形式
        req = GenerateRequest(prompt="test", width=512, height=256)
        result = generate_single(req, reset_state)
        assert result["dimensions"] == "512x256"

    def test_result_steps_matches_request(self, mock_pipeline, reset_state):
        # stepsがリクエストのnum_inference_stepsと一致する
        req = GenerateRequest(prompt="test", num_inference_steps=8)
        result = generate_single(req, reset_state)
        assert result["steps"] == 8

    def test_result_generation_time_is_positive(self, mock_pipeline, reset_state):
        # generation_time_secondsが正の数値
        req = GenerateRequest(prompt="test")
        result = generate_single(req, reset_state)
        assert result["generation_time_seconds"] >= 0

    def test_result_path_is_within_output_dir(self, mock_pipeline, reset_state):
        # pathが出力ディレクトリ内を指す
        req = GenerateRequest(prompt="test")
        result = generate_single(req, reset_state)
        assert str(reset_state) in result["path"]
