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

制約と回避策は `docs/MODEL_CHARACTERISTICS.md` を参照（403枚テスト済み）。最重要の制約:

- **否定表現(without/no)は完全に無視される** — 肯定的な別描写に言い換える
- **テキスト描画は不可** — 後加工で対応
- **人物クローズアップはアニメ調に収束** — リアル→`Canon EOS R5`/UE5、ドット→Minecraft/sprite sheet で迂回
- **ポップアート/ローポリ/パステルは不安定** — 複合スタイルで補強するか避ける
- **花/地形はスタイル差が出にくい** — 地形のアニメ/ドット化は効かない
- **512×512 / 4ステップが推奨** — 768以上はスタイル変化リスク、8ステップはドット絵劣化

## Known Issues

- batch_jobs はインメモリ dict のみ（サーバー再起動で消失）
