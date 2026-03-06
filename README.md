# flux-local-image-gen

FLUX.1-schnell を OpenVINO 経由で Intel Arc GPU で動かすローカル画像生成 API サーバー。
他プロジェクトから HTTP 経由で画像生成を依頼する用途。

## Prerequisites

### Hardware
- **Intel Arc GPU** が必須（Intel Arc 140V で動作確認済み）
- VRAM 8GB 以上推奨

### Software
- Python 3.10+
- Windows 11
- Intel GPU ドライバ（最新版）

### GPU 認識の確認方法

```powershell
# Python から OpenVINO が GPU を認識しているか確認
python -c "from openvino import Core; print(Core().available_devices)"
# 出力に 'GPU' が含まれていれば OK
# ['CPU', 'GPU', 'NPU'] のような出力が期待値
```

GPU が認識されない場合:
1. デバイスマネージャーで Intel Arc GPU が正常に認識されているか確認
2. Intel 公式サイトから最新の GPU ドライバをインストール
3. PC を再起動して再確認

## Setup

AIエージェント（Claude Code 等）に以下のプロンプトを渡すだけでセットアップできます:

> **flux-local-image-gen をセットアップして。**
> リポジトリ: https://github.com/ShoYasuda-rex/flux-local-image-gen.git
> 手順: clone → python venv作成 → pip install -r requirements.txt → huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8 → python api_server.py でサーバー起動（ポート8188）。モデルDLは約15.7GB。初回起動時のモデルロードに約120秒かかる。

<details>
<summary>手動セットアップ手順</summary>

```powershell
# 1. リポジトリをクローン
git clone https://github.com/ShoYasuda-rex/flux-local-image-gen.git
cd flux-local-image-gen

# 2. venv 作成・有効化
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. 依存インストール
pip install -r requirements.txt

# 4. モデルダウンロード（約 15.7GB、回線速度により 10〜30 分）
huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8
```

</details>

### モデルダウンロードが途中で止まった場合

同じコマンドを再実行すれば途中から再開される（huggingface-cli は自動レジューム対応）。

```powershell
huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8
```

### モデルの整合性確認

```powershell
# transformer モデル（最大ファイル）が正しくダウンロードされたか確認
python -c "from pathlib import Path; p=Path('models/flux1-schnell-int8/transformer/openvino_model.bin'); print(f'Size: {p.stat().st_size / (1024**3):.2f} GB') if p.exists() else print('NOT FOUND')"
# 数 GB 以上のサイズが表示されれば OK。NOT FOUND やサイズが極端に小さい場合は再ダウンロード
```

## Usage

### サーバー起動

```powershell
# PowerShell
.\start_server.ps1

# または直接実行
.\venv\Scripts\Activate.ps1
python api_server.py
```

```bash
# Git Bash / Claude Code から起動する場合
# ※ source venv/Scripts/activate は Git Bash では効かない
./venv/Scripts/python.exe api_server.py
```

初回起動時はモデルロードに約 120 秒かかる。`Pipeline loaded in XXs` のログが出れば準備完了。

### 動作確認

```powershell
# ヘルスチェック（model_loaded が true になるまで待つ）
curl http://127.0.0.1:8188/health

# テスト生成
curl -X POST http://127.0.0.1:8188/generate -H "Content-Type: application/json" -d "{\"prompt\": \"a cat sitting on a windowsill\", \"num_inference_steps\": 4, \"height\": 512, \"width\": 512}"
```

## API Reference

Base URL: `http://127.0.0.1:8188`

### POST /generate

1 枚生成（同期）。約 16〜19 秒で応答。

```json
{
  "prompt": "a cat sitting on a windowsill",
  "num_inference_steps": 4,
  "height": 512,
  "width": 512,
  "filename": "cat.png",
  "remove_bg": false
}
```

`prompt` 以外は省略可。デフォルト: 4 steps, 512x512。
`remove_bg: true` で黒背景を透過 PNG に変換。

**レスポンス例:**
```json
{
  "filename": "cat_a1b2.png",
  "path": "C:/path/to/outputs/cat_a1b2.png",
  "prompt": "a cat sitting on a windowsill",
  "generation_time_seconds": 17.3,
  "dimensions": "512x512",
  "steps": 4
}
```

### POST /batch

複数枚を非同期バッチ生成。即座に job_id を返す。

```json
{
  "prompts": [
    { "prompt": "a red dragon", "filename": "dragon.png" },
    { "prompt": "a blue castle", "filename": "castle.png" }
  ]
}
```

**レスポンス例:**
```json
{
  "job_id": "a1b2c3d4e5f6",
  "total": 2,
  "output_dir": "C:/path/to/outputs/20260306_1200_a_red_dragon"
}
```

### GET /batch/{job_id}

バッチジョブの進捗を確認。`status` が `"completed"` になるまでポーリング。

### GET /health

```json
{ "status": "ok", "model_loaded": true }
```

`model_loaded` が `false` の間はまだモデルロード中。

### GET /outputs/{filename}

生成画像を直接取得（PNG）。

## Performance

| 項目 | 値 |
|------|-----|
| モデル | FLUX.1-schnell INT8 |
| GPU | Intel Arc 140V |
| 推論ステップ | 4 |
| 解像度 | 512x512 |
| 生成時間 | 約 16〜19 秒/枚 |
| 初回ロード | 約 120 秒 |

512x512 / 4 ステップがコスパ最良。ステップ数を増やしても画質向上は限定的。

## Troubleshooting

| 症状 | 原因と対策 |
|------|-----------|
| `No module named 'optimum'` | venv が有効化されていない。`.\venv\Scripts\Activate.ps1` を実行 |
| `Pipeline loaded` が出ない | モデルが未ダウンロードまたは不完全。`huggingface-cli download` を再実行 |
| `RuntimeError: GPU device not found` | Intel GPU ドライバが未インストール。上記「GPU 認識の確認方法」を参照 |
| 生成が極端に遅い（60 秒以上） | GPU ではなく CPU で推論している可能性。OpenVINO の GPU 対応を確認 |
| `OSError: model not found` | `models/flux1-schnell-int8/` のパスが間違っている。ディレクトリ構造を確認 |
| ポート 8188 が使用中 | 他のプロセスが 8188 を使っている。`netstat -ano | findstr 8188` で確認 |

## Tech Stack

- [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) — Black Forest Labs の高速画像生成モデル
- [OpenVINO](https://github.com/openvinotoolkit/openvino) — Intel ハードウェア向け推論最適化
- [optimum-intel](https://github.com/huggingface/optimum-intel) — HuggingFace + OpenVINO 統合
- [FastAPI](https://fastapi.tiangolo.com/) — API サーバー
