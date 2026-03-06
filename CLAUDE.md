# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

FLUX.1-schnell をOpenVINO経由でIntel Arc 140V GPUで動かすローカル画像生成APIサーバー。
他プロジェクトからHTTP経由でアセット生成を依頼する用途。

## Commands

```powershell
# サーバー起動（初回モデルロード約120秒）
.\start_server.ps1

# パイプライン単体テスト（サーバー不要、1枚生成）
.\venv\Scripts\Activate.ps1
python test_generate.py

# バッチAPIテスト（サーバー起動中に実行）
python test_batch_api.py
```

```bash
# Claude Code（Git Bash）からサーバー起動する場合
# ※ source venv/Scripts/activate は効かないので venv の python を直接指定
./venv/Scripts/python.exe api_server.py
```

## Architecture

```
api_server.py          ← FastAPIサーバー（本体）。全APIエンドポイントとパイプライン管理
  OVFluxPipeline       ← optimum-intel経由でOpenVINO IRモデルをGPU推論
  threading.Lock       ← パイプラインはシングルスレッド推論、lockで排他制御
  daemon Thread        ← /batch は非同期実行（スレッド起動→即レスポンス→ポーリング確認）

models/flux1-schnell-int8/  ← OpenVINO IR形式の変換済みモデル（15.7GB）
outputs/                    ← 生成画像の出力先（/generate: 直下、/batch: サブフォルダ）
```

API: `http://127.0.0.1:8188`
- `POST /generate` — 同期1枚生成（約16-19秒）
- `POST /batch` — 非同期バッチ生成（job_id返却）
- `GET /batch/{job_id}` — ジョブ進捗確認
- `GET /health` — モデルロード状態
- `GET /outputs/{filename}` — 画像取得

## Key Decisions

- **FLUX.1-schnell**（devではない）: 4ステップ/16-19秒。プロトタイプ用途に十分
- **FastAPI直ラップ**（ComfyUIではない）: ComfyUIはCUDA前提でIntel GPU非対応
- **変換済みモデル直接DL**（自前変換ではない）: `OpenVINO/FLUX.1-schnell-int8-ov` を使用、変換時のバージョン不整合を回避

## Model Characteristics

詳細は `docs/MODEL_CHARACTERISTICS.md` を参照。要点:

- **人物クローズアップはアニメ調に収束**（リアル/ドット指定が効かない）
  - 迂回策: リアル→カメラ機種名(Canon EOS R5等)、ドット→Minecraft/sprite sheet指定
  - 水彩/フラット/ちび/浮世絵等の具体的画風は人物でも効く
- **アイテム・乗り物・建物・動物はスタイル制御◎**
- **512×512 / 4ステップが推奨**（コスパ最良）
- テキスト描画は不可

## Known Issues

- batch_jobs はインメモリ dict のみ（サーバー再起動で消失）
