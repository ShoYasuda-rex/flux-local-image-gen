"""_slugify_prompt 関数のユニットテスト。
プロンプト文字列からファイル名用のスラッグを正しく生成できることを検証する。
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_server import _slugify_prompt


class TestSlugifyPromptBasic:
    """基本的なスラッグ生成の検証"""

    def test_simple_english_prompt(self):
        # 英単語のみのプロンプトがアンダースコア区切りに変換される
        result = _slugify_prompt("a small robot")
        assert result == "a_small_robot"

    def test_converts_to_lowercase(self):
        # 大文字が小文字に変換される
        result = _slugify_prompt("A Big Castle")
        assert result == "a_big_castle"

    def test_special_characters_replaced_with_underscore(self):
        # 特殊文字がアンダースコアに置換される
        result = _slugify_prompt("red+blue & green!")
        assert result == "red_blue_green"

    def test_leading_trailing_underscores_stripped(self):
        # 先頭・末尾のアンダースコアが除去される
        result = _slugify_prompt("  hello world  ")
        assert result == "hello_world"

    def test_consecutive_special_chars_become_single_underscore(self):
        # 連続する特殊文字が1つのアンダースコアに集約される
        result = _slugify_prompt("a---b___c")
        assert result == "a_b_c"


class TestSlugifyPromptNoiseRemoval:
    """汎用ワード（ノイズ）の除去を検証"""

    def test_removes_pixel_art(self):
        # "pixel art" が除去される
        result = _slugify_prompt("pixel art a small robot")
        assert "pixel" not in result
        assert "art" not in result
        assert "small_robot" in result

    def test_removes_game_sprite(self):
        # "game sprite" が除去される
        result = _slugify_prompt("game sprite a sword")
        assert "game" not in result
        assert "sprite" not in result

    def test_removes_black_background(self):
        # "black background" が除去される
        result = _slugify_prompt("a cat black background")
        assert "black" not in result
        assert "background" not in result

    def test_removes_multiple_noise_words(self):
        # 複数のノイズワードが同時に除去される
        result = _slugify_prompt("pixel art game sprite a robot no anti-aliasing")
        assert "pixel" not in result
        assert "game" not in result
        assert "robot" in result


class TestSlugifyPromptMaxLength:
    """最大文字数制限の検証"""

    def test_default_max_length_48(self):
        # デフォルトで48文字以内に切り詰められる
        long_prompt = "a " * 100  # 非常に長いプロンプト
        result = _slugify_prompt(long_prompt)
        assert len(result) <= 48

    def test_custom_max_length(self):
        # カスタムmax_lenが適用される
        result = _slugify_prompt("a very long prompt with many words here", max_len=10)
        assert len(result) <= 10

    def test_trailing_underscore_removed_after_truncation(self):
        # 切り詰め後の末尾アンダースコアが除去される
        # "abcde_fghij" を max_len=6 で切ると "abcde_" → "abcde" になるはず
        result = _slugify_prompt("abcde fghij", max_len=6)
        assert not result.endswith("_")


class TestSlugifyPromptEdgeCases:
    """エッジケースの検証"""

    def test_empty_string_returns_image(self):
        # 空文字列の場合はデフォルト "image" が返る
        result = _slugify_prompt("")
        assert result == "image"

    def test_only_noise_words_returns_image(self):
        # ノイズワードのみの場合はデフォルト "image" が返る
        result = _slugify_prompt("pixel art game sprite")
        assert result == "image"

    def test_only_special_characters_returns_image(self):
        # 特殊文字のみの場合はデフォルト "image" が返る
        result = _slugify_prompt("!@#$%^&*()")
        assert result == "image"

    def test_numbers_preserved(self):
        # 数字が保持される
        result = _slugify_prompt("32x32 sprite")
        assert "32x32" in result

    def test_japanese_characters_removed(self):
        # 日本語文字は除去される（a-z0-9のみ保持）
        result = _slugify_prompt("ロボット robot")
        assert result == "robot"
