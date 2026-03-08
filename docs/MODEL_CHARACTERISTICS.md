# FLUX.1-schnell INT8 OpenVINO モデル特徴

403枚の生成テスト結果に基づく。

## 1. 制約と落とし穴（必読）

プロンプト生成前に必ず確認すること。

### 絶対に効かないもの

| 制約 | 詳細 |
|------|------|
| **否定表現** | `without`, `no ~` は完全に無視される（10件中9件×）。「翼なし龍」→翼が描かれる。「弦なしギター」→弦6本見える |
| **テキスト描画** | 漢字・英語とも読める文字は生成不可。テキストが必要なら後加工 |

### 効かない被写体×スタイルの組み合わせ

| 被写体 | 効かないスタイル | 何が起きるか |
|--------|----------------|-------------|
| **人物クローズアップ** | リアル / ドット絵 | 全てアニメ調に収束。`photorealistic`も`pixel art`も無視される |
| **花・植物** | リアル↔アニメの区別 | 柔らかい描写に収束し3スタイル間の差が出ない |
| **地形テクスチャ** | アニメ / ドット絵 | リアル写真風に収束。スタイル制御が最も困難な被写体 |
| **食べ物** | リアル↔アニメの区別 | 両者が近い。ドット絵は効く |
| **生き物全般** | ローポリ3D | 猫等でポリゴン面が全く出ずフォトリアル化する |

### 不安定なスタイル（スタイル崩壊リスク高）

| スタイル | 問題 | 回避策 |
|---------|------|--------|
| **ポップアート** | 被写体の記述（ダーク/氷系等）がスタイル指定を上書きし崩壊 | 回避策なし。複数生成から選別が必要 |
| **ローポリ3D** | 生き物・人物で完全失敗。剣等の無機物でのみ効く | 生き物には使わない |
| **パステル** | 「柔らかい色」止まりでチョーク質感に到達しない | フラットデザインと複合で補強: `soft pastel colors, flat design, vector art` |
| **アイソメトリック** | 視点角度にブレが残る。アイレベルやwormseye寄りになることがある | `isometric pixel art, game asset, 3D voxel style` と専門用語を追加 |
| **斜め45度構図** | アイレベルや見上げとの区別が曖昧になりやすい | 俯瞰/アイレベル/見上げの3構図を使う |

### 生成パラメータの注意

| 注意点 | 詳細 |
|--------|------|
| **768以上でスタイル変化** | フラット指定が描き込み寄りになる等、意図しないスタイル変化が起きる |
| **8ステップでドット絵劣化** | ステップを増やすとドット感が薄れる。ドット絵は4ステップ固定 |
| **pixel指定は人物クローズアップで薄まる** | 全身構図なら効くが、バストアップではピクセル感が消える |

### その他の副作用

- `Japanese aesthetic` 系プロンプトで意味不明な漢字風文字が画面に出現する
- Minecraft風生成時に「cyconts」等の意味不明テキストが出現する癖がある
- 宇宙背景を指定すると被写体がファンタジー調に寄る傾向がある

## 2. 制約の回避策

### 人物のスタイル制御

人物はデフォルトでアニメ調に収束する。以下で突破可能:

| 目的 | 回避策 | キーワード |
|------|--------|----------|
| リアル化 | カメラ機種名で突破 | `Canon EOS R5, 85mm f1.4, shallow depth of field` |
| リアル化 | 3DCG文脈で突破 | `Unreal Engine 5, subsurface scattering, ray tracing, 8k textures, cinematic lighting` |
| ドット化 | ボクセルとして指定 | `Minecraft character, voxel human, blocky 3D, cube-based` |
| ドット化 | スプライトシートとして指定 | `RPG game sprite sheet, 32x32 pixel character, top-down view` |

- `portrait photograph` より `Canon EOS R5` のほうが強い
- 単なる `pixel art` では人物に効かない
- 水彩/油絵/フラット/鉛筆スケッチ/浮世絵/ちび/サイバーパンク/版画は人物でも確実に効く

### 否定表現の言い換え

否定は機能しないため、肯定的な別描写に変換する:

| NG | OK | 理由 |
|----|------|------|
| `dragon without wings` | `Chinese serpentine dragon, long snake-like body` | 別カテゴリの龍として指定 |
| `sword without hilt` | `a bare sword blade, detached from hilt` | 状態を肯定的に描写 |
| `car without wheels` | `hovering car, futuristic, no undercarriage` | 別コンセプトとして再定義 |

### 不安定スタイルの安定化（専門用語3つルール）

スタイル名だけでは不安定なスタイルも、**固有の専門用語を3つ以上追加**すると安定する:

| スタイル | NG（不安定） | OK（安定） |
|---------|------------|-----------|
| UE5リアル | `warrior, UE5, ray tracing` | `battle-hardened warrior, Unreal Engine 5, subsurface scattering, ray tracing, 8k textures, cinematic lighting` |
| レトロ80s | `warrior, retro 80s style` | `warrior in neon retrowave style, 1980s aesthetic, synthwave, VHS scan lines, hot pink and cyan` |
| Minecraft | `pixel art warrior, Minecraft` | `Minecraft character warrior, voxel human, blocky 3D, cube-based, diamond armor, pickaxe` |
| 鉛筆スケッチ | `pencil sketch of warrior` | `pencil sketch of a warrior, graphite drawing, hatching, rough lines, sketchbook page, detailed crosshatching` |

### 弱いスタイルの複合補強

単体で△のスタイルも、安定したスタイルと複合すると◎になる。2スタイル掛け合わせは全テストで成功（25/25）:

| 弱いスタイル | 補強の組み合わせ | キーワード |
|------------|----------------|----------|
| パステル(△) | +フラットデザイン | `soft pastel colors, flat design, vector art, minimal, clean shapes, dreamy` |
| アイソメトリック(○) | +ドット絵 | `isometric pixel art, 16-bit style, blocky pixels, isometric perspective` |
| ダークファンタジー(○) | +油絵 | `oil painting, thick brushstrokes, dark fantasy atmosphere, dramatic chiaroscuro` |
| 浮世絵 | +サイバーパンク | `cyberpunk neon aesthetic with ukiyo-e Japanese woodblock print style` |
| ちび | +水彩 | `watercolor painting, soft washes, chibi style, super deformed, kawaii` |

## 3. 被写体別のスタイル制御力

| 被写体 | リアル↔アニメ | ドット絵 | 水彩/油絵/フラット等 | 備考 |
|------|:---:|:---:|:---:|------|
| **人物（クローズアップ）** | × | × | ○ | アニメ調に収束。回避策はセクション2 |
| **人物（群衆・遠景）** | △ | △ | ○ | 人が小さいと差が出やすい |
| **人物（ファンタジーキャラ）** | △ | △ | ○ | エルフ等はリアルがやや出る |
| **動物（猫等）** | ○ | ◎ | ◎ | 全スタイル対応 |
| **車・乗り物** | ◎ | ◎ | ○ | 3スタイル明確に分離 |
| **建物・風景** | ◎ | ◎ | ○ | 3スタイル明確に分離 |
| **アイテム（剣・宝箱等）** | ◎ | ◎ | ○ | スタイル制御が最も効く |
| **食べ物** | × | ○ | ○ | リアルとアニメが近い |
| **メカ・ロボット** | ○ | ◎ | ○ | ドットが特に効く |
| **ドラゴン等モンスター** | ○ | ◎ | ○ | ドットが特に効く |
| **植物・花** | △ | △ | ○ | スタイル差が出にくい |
| **宝石・鉱石** | ◎ | ○ | ◎ | アイテム系と同等 |
| **魔法エフェクト** | ○ | ◎ | ○ | プロンプトの具体性が重要 |
| **地形テクスチャ** | ◎ | × | △ | リアル以外は効かない |
| **UI要素** | ○ | ◎ | ◎ | スタイル差が出やすい |

色指定・背景制御・構図制御（俯瞰/アイレベル/見上げ）は全被写体で安定して効く。

## 4. 生成パラメータ

| パラメータ | 推奨値 | 備考 |
|-----------|-------|------|
| サイズ | **512×512** | コスパ最良。256は細部潰れ、768以上はスタイル変化リスク |
| ステップ | **4** | schnellの設計値。8ステップはリアル系のみ検討、ドット絵には逆効果 |
| 生成時間目安 | 512: ~14秒、768: ~55秒、1024: ~120秒 | |

## 5. プロンプト設計のアンチパターン

| パターン | 問題 | 改善 |
|---------|------|------|
| 装備リスト型 | `warrior, plate armor, great sword, shield, heroic stance` → 凡庸な絵 | キャラに物語を: `grizzled veteran resting on battle axe, scars across face` |
| コピペ差し替え | スタイルキーワードだけ変えて同じ文面 → 品質低下 | スタイルに合わせて描写も変える（水彩→soft/gentle、油絵→thick/heavy） |
| 否定制約の詰め込み | `no anti-aliasing, sharp pixels, clean edges` → 無視される | 肯定表現のみ使う |
| スタイル名だけ | `pixel art warrior` → 不安定 | 専門用語を3つ以上追加（セクション2参照） |

## 6. RPGキャラ生成の注意点

100枚テスト（8職業×5スタイル + 8敵種×5スタイル + シーン20枚）で判明した地雷:

### キャラの落とし穴

| 問題 | 詳細 | 対策 |
|------|------|------|
| **healer/paladin混同** | 両方「白+杖+光」で小サイズだと区別不能 | paladinに`shield, cross emblem`、healerに`crystal staff, gentle expression` |
| **thiefが忍者化** | 黒フード+ダガーが忍者/アサシンに振れる | `lockpick, coin pouch, sly grin` 等の盗賊固有アイテムを追加 |
| **pixelスタイルの不安定** | クローズアップでピクセル感が消える（healer/mage/samurai） | 全身構図にするか、chibi/flatを使う |
| **animeスタイルの幅** | セル塗り/厚塗り/コミック調が混在し統一感が出にくい | 統一感が必要ならchibiかflatを使う |
| **vampireのアニメ収束** | 人物クローズアップのため既知の制約が発動 | darkfantasyスタイルなら許容範囲 |

### シーン・アイテムの落とし穴

| 問題 | 詳細 | 対策 |
|------|------|------|
| **ボス戦のスケール感** | 対等な2人の戦闘に見えてボス戦感が薄れる | `towering boss`, `tiny party` でスケール差を明示 |
| **snowマップタイル** | 水滴風になり雪原に見えない | `white snow ground with subtle blue shadows, seamless tileable` |
| **マップタイルの継ぎ目** | シームレスタイリング未保証 | `seamless tileable, top-down, game tile` を必ず含める |

### RPGキャラに安定するスタイル

chibi > flat > darkfantasy(敵向き) > watercolor の順に安定。pixelとanimeは上記の問題あり。
