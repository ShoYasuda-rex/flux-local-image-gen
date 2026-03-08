"""load_pipeline 関数のユニットテスト。
ダブルチェックロッキングパターン、グローバルpipe変数の管理を検証する。
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# optimum.intel をモック化してからインポート
mock_ov_module = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.intel"] = mock_ov_module

import api_server
from api_server import load_pipeline


@pytest.fixture(autouse=True)
def reset_pipe():
    """各テスト前にpipeをNoneにリセットし、from_pretrainedモックもリセットする。"""
    original_pipe = api_server.pipe
    api_server.pipe = None
    # sys.modules内のモックを取得してリセット
    ov_mock = sys.modules["optimum.intel"]
    ov_mock.OVFluxPipeline.from_pretrained.reset_mock()
    yield
    api_server.pipe = original_pipe


class TestLoadPipelineDoubleCheck:
    """ダブルチェックロッキングパターンの検証"""

    def test_returns_existing_pipe_without_lock(self):
        # pipeが既にロード済みの場合、lockを取得せず即座に返す
        sentinel = MagicMock(name="already_loaded_pipe")
        api_server.pipe = sentinel
        result = load_pipeline()
        assert result is sentinel

    def test_loads_pipeline_when_none(self):
        # pipeがNoneの場合、OVFluxPipelineをロードしてグローバルpipeに設定する
        mock_pipeline_instance = MagicMock(name="new_pipeline")
        ov_mock = sys.modules["optimum.intel"]
        ov_mock.OVFluxPipeline.from_pretrained.return_value = mock_pipeline_instance

        result = load_pipeline()

        assert result is mock_pipeline_instance
        # グローバルpipeが更新される
        assert api_server.pipe is mock_pipeline_instance

    def test_from_pretrained_called_with_gpu(self):
        # from_pretrainedがdevice="GPU"で呼ばれる
        mock_pipeline_instance = MagicMock()
        ov_mock = sys.modules["optimum.intel"]
        ov_mock.OVFluxPipeline.from_pretrained.return_value = mock_pipeline_instance

        load_pipeline()

        call_kwargs = ov_mock.OVFluxPipeline.from_pretrained.call_args
        assert call_kwargs is not None, "from_pretrained was not called"
        assert call_kwargs[1]["device"] == "GPU"

    def test_from_pretrained_called_with_latency_hint(self):
        # from_pretrainedのov_configにPERFORMANCE_HINT=LATENCYが設定される
        mock_pipeline_instance = MagicMock()
        ov_mock = sys.modules["optimum.intel"]
        ov_mock.OVFluxPipeline.from_pretrained.return_value = mock_pipeline_instance

        load_pipeline()

        call_kwargs = ov_mock.OVFluxPipeline.from_pretrained.call_args
        assert call_kwargs is not None, "from_pretrained was not called"
        assert call_kwargs[1]["ov_config"]["PERFORMANCE_HINT"] == "LATENCY"

    def test_second_call_returns_cached_pipe(self):
        # 2回目の呼び出しはキャッシュされたpipeを返す（from_pretrainedは1回のみ）
        mock_pipeline_instance = MagicMock(name="cached_pipe")
        ov_mock = sys.modules["optimum.intel"]
        ov_mock.OVFluxPipeline.from_pretrained.return_value = mock_pipeline_instance

        result1 = load_pipeline()
        call_count_after_first = ov_mock.OVFluxPipeline.from_pretrained.call_count

        result2 = load_pipeline()

        assert result1 is result2
        # 2回目ではfrom_pretrainedが追加で呼ばれていない
        assert ov_mock.OVFluxPipeline.from_pretrained.call_count == call_count_after_first

    def test_cache_dir_created(self):
        # load_pipeline実行後、model_cacheディレクトリが作成される
        mock_pipeline_instance = MagicMock()
        ov_mock = sys.modules["optimum.intel"]
        ov_mock.OVFluxPipeline.from_pretrained.return_value = mock_pipeline_instance

        load_pipeline()

        call_kwargs = ov_mock.OVFluxPipeline.from_pretrained.call_args
        assert call_kwargs is not None
        assert "CACHE_DIR" in call_kwargs[1]["ov_config"]
