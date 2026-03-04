# flux-local-image-gen

FLUX.1-schnell を OpenVINO 経由で Intel Arc GPU（Intel Arc 140V）で動かすローカル画像生成 API サーバー。
他プロジェクトから HTTP 経由でアセット生成を依頼する用途。

## 動作環境

- Intel Arc GPU（Intel Arc 140V で動作確認済み）
- Python 3.10+
- OpenVINO 2024.x+
- Windows 11

## セットアップ

```powershell
# 1. venv 作成・有効化
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. 依存インストール
pip install -r requirements.txt

# 3. モデルダウンロード（約15.7GB）
huggingface-cli download OpenVINO/FLUX.1-schnell-int8-ov --local-dir models/flux1-schnell-int8

# 4. サーバー起動（初回モデルロード約120秒）
.\start_server.ps1
# または
python api_server.py
```

## API エンドポイント

ベース URL: `http://127.0.0.1:8188`

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/generate` | 1枚生成（同期） |
| POST | `/batch` | バッチ生成（非同期、job_id 返却） |
| GET | `/batch/{job_id}` | ジョブ進捗確認 |
| GET | `/health` | ヘルスチェック |
| GET | `/outputs/{filename}` | 生成画像取得 |

### POST /generate

```json
{
  "prompt": "a cat sitting on a windowsill",
  "num_inference_steps": 4,
  "height": 512,
  "width": 512,
  "filename": "cat.png"
}
```

`num_inference_steps`, `height`, `width`, `filename` は省略可。

## パフォーマンス

| 項目 | 値 |
|------|-----|
| モデル | FLUX.1-schnell INT8 |
| GPU | Intel Arc 140V |
| 推論ステップ | 4 |
| 解像度 | 512x512 |
| 生成時間 | 約16〜19秒/枚 |
| 初回ロード | 約120秒 |

## 技術スタック

- [FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell) — Black Forest Labs の高速画像生成モデル
- [OpenVINO](https://github.com/openvinotoolkit/openvino) — Intel ハードウェア向け推論最適化
- [optimum-intel](https://github.com/huggingface/optimum-intel) — HuggingFace + OpenVINO 統合
- [FastAPI](https://fastapi.tiangolo.com/) — API サーバー
