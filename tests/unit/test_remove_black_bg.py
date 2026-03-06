"""_remove_black_bg 関数のユニットテスト。
黒背景をRGBA透明に変換するロジックを検証する。
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_server import _remove_black_bg


class TestRemoveBlackBgBasic:
    """基本的な黒背景除去の検証"""

    def test_pure_black_becomes_transparent(self):
        # 純粋な黒ピクセル(0,0,0)が透明(alpha=0)になる
        img = Image.new("RGB", (2, 2), (0, 0, 0))
        result = _remove_black_bg(img)
        data = np.array(result)
        # 全ピクセルのalphaが0であること
        assert (data[:, :, 3] == 0).all()

    def test_white_stays_opaque(self):
        # 白ピクセル(255,255,255)はそのまま不透明(alpha=255)
        img = Image.new("RGB", (2, 2), (255, 255, 255))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert (data[:, :, 3] == 255).all()

    def test_colored_pixel_stays_opaque(self):
        # 明るい色のピクセルは不透明のまま
        img = Image.new("RGB", (2, 2), (200, 100, 50))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert (data[:, :, 3] == 255).all()

    def test_output_is_rgba(self):
        # 出力画像がRGBAモードであること
        img = Image.new("RGB", (2, 2), (128, 128, 128))
        result = _remove_black_bg(img)
        assert result.mode == "RGBA"


class TestRemoveBlackBgThreshold:
    """閾値に関する検証"""

    def test_near_black_within_default_threshold(self):
        # デフォルト閾値(30)以下の暗いピクセルが透明になる
        img = Image.new("RGB", (1, 1), (25, 25, 25))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert data[0, 0, 3] == 0

    def test_just_above_default_threshold_stays_opaque(self):
        # デフォルト閾値(30)を超えるピクセルは不透明のまま
        img = Image.new("RGB", (1, 1), (31, 31, 31))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert data[0, 0, 3] == 255

    def test_custom_threshold(self):
        # カスタム閾値が正しく適用される
        img = Image.new("RGB", (1, 1), (50, 50, 50))
        # 閾値60なら透明
        result = _remove_black_bg(img, threshold=60)
        data = np.array(result)
        assert data[0, 0, 3] == 0

    def test_one_channel_above_threshold_stays_opaque(self):
        # 1チャンネルでも閾値を超えていれば不透明のまま
        # （全チャンネルが閾値以下の場合のみ透明化される）
        img = Image.new("RGB", (1, 1), (0, 0, 31))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert data[0, 0, 3] == 255


class TestRemoveBlackBgMixedImage:
    """黒背景と前景が混在する画像の検証"""

    def test_mixed_image_preserves_foreground(self):
        # 黒背景上に白い前景がある画像で、前景が保持される
        img = Image.new("RGB", (4, 4), (0, 0, 0))
        # 中央2x2を白に
        for x in range(1, 3):
            for y in range(1, 3):
                img.putpixel((x, y), (255, 255, 255))
        result = _remove_black_bg(img)
        data = np.array(result)
        # 黒背景部分（角）は透明
        assert data[0, 0, 3] == 0
        # 白い前景部分は不透明
        assert data[1, 1, 3] == 255

    def test_rgba_input_handled(self):
        # RGBA入力画像も正しく処理される
        img = Image.new("RGBA", (2, 2), (0, 0, 0, 255))
        result = _remove_black_bg(img)
        data = np.array(result)
        assert (data[:, :, 3] == 0).all()
