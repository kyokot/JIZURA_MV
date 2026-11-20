# モデルとシーンの書式

## 目次
- モデル：座標系／JSON の部品／.vox／スライスシート／確認と変換
- シーン：全体の設定／カメラ／物体／式で使える変数と関数／キーフレーム
- composite の層の指定

---

## モデル

### 座標系

単位はボクセル（＝1ドット）。`x` は右、`y` は手前（yaw 0 のときカメラ側）、`z` は上。
モデルは `z` ごとのスライスの積み重ねとして保持され、回転の軸は底面の中心（`pivot` で変更可）。

### JSON で部品を組む

```json
{
  "size": [20, 14, 26],
  "palette": {"body": "#2b2d42", "cone": "#edf2f4"},
  "parts": [
    {"type": "box", "from": [0, 0, 2], "to": [20, 14, 26], "color": "body", "color_top": "#3d405b"},
    {"type": "ellipsoid", "center": [10, 14, 10], "radii": [5, 2.5, 5], "color": "cone"}
  ]
}
```

- `size`：[幅 x, 奥行き y, 高さ z]。省くと部品に合わせて自動で決まる。
- `palette`：色に名前を付ける。色は `"#rrggbb"`（`"#rrggbbaa"` も可）か palette の名前。
- 部品は上から順に描かれ、後の部品が前の部品を上書きする。どの部品にも `"erase": true` を付けると、その形でくり抜く。
- どの立体の部品にも `color_top` を付けると、下から上へのグラデーションになる。

| type | 必要な項目 | 用途 |
|---|---|---|
| `box` | `from` [x,y,z], `to` [x,y,z]（to は含まない） | 箱、建物、機材 |
| `cylinder` | `center` [x,y], `radius`, `z` [z0,z1]。`radius_top` で先細り | 柱、円錐、幹 |
| `sphere` / `ellipsoid` | `center` [x,y,z], `radius` または `radii` [rx,ry,rz] | 球、丸い出っ張り |
| `lathe` | `center` [x,y], `radii`（スライスごとの半径の並び）, `z0`, `colors`（スライスごとの色、足りなければ繰り返す） | 提灯、壺、瓶、木。回転体はこれが一番楽 |
| `layers` | `rows`（文字の行の配列＝1スライス、またはその配列＝下からのスライス群）, `key`（文字→色）, `at` [x,y], `z` [z0,z1] または `z0` | 手描きのドット絵を輪切りで指定 |
| `flat` | `image`（PNG）, `at` [x,y,z], `depth`（厚み） | 画像を地面に寝かせて上へ押し出す（看板、ロゴ、床の模様） |
| `upright` | `image`（PNG）, `at` [x,y,z], `depth` | 画像を立てる（キャラの正面絵、パネル）。yaw 0 で正面がカメラを向く |
| `text` | `text`, `font`（.ttf/.otf のパス。省くと OS の日本語フォント）, `font_size`, `color`, `mode`（`upright` 既定／`flat`）, `depth` | 文字を立体にする |

`layers` の例（3×3 の輪を2枚重ねる）：

```json
{"type": "layers", "z": [0, 2], "at": [4, 4], "key": {"#": "#ffcc00"}, "rows": ["###", "#.#", "###"]}
```

部品が1つだけの文字・画像モデルは短く書ける：

```json
{"text": "音", "font_size": 34, "depth": 2, "mode": "upright", "color": "#fff6d6"}
{"image": "character.png", "depth": 2}
```

画像は不透明な画素だけがボクセルになる（アルファ 128 未満は捨てる）。画像のパスはモデルの JSON からの相対パス。
文字はアンチエイリアスを切って2値化する（ドット絵にするため）。細い書体は `font_size` を上げるか太い書体を使う。

### MagicaVoxel の .vox

そのまま読める（ファイル内の最初のモデル。パレットも読む）。手で形を作り込みたいときはこれが一番速い。
シーンからは `"model": "car.vox"` と書くだけ。

### スライスシート PNG

スライスを横一列に並べた画像（左端が一番下のスライス）。Aseprite などで描いたもの、配布されているスタック素材がこの形。

- シーンでは `"model": "car.png", "slices": 16` のように枚数を添える。省くと正方形のセルとして割る。
- 縦並びは `"layout": "vertical"`、格子は `"slice_size": [幅, 高さ]`（左上から右へ、行ごとに）、上のスライスが先頭なら `"top_first": true`。

### 確認と変換

```sh
SS model lantern.json                      # 大きさとボクセル数を表示
SS model lantern.json -o lantern_sheet.png # スライスシートに変換（Aseprite で手直し → PNG として読み直せる）
SS turntable lantern.json -o spin.gif      # 回転 GIF
SS turntable lantern.json -o dirs.png --frames 16 --squash 0.6 --outline "#000"
```

`turntable` の PNG は全方向を並べた1枚で、確認用にも、ゲームや AE で使う「回転済みスプライトシート」としても使える。

---

## シーン

```json
{
  "width": 1920, "height": 1080, "fps": 24, "pixel_scale": 6,
  "bpm": 128, "offset": 0.35, "beats": 32, "anim_fps": 12,
  "background": {"gradient": ["#141428", "#2a1838"]},
  "floor": {"size": 20, "colors": ["#241c3a", "#2e2448"], "radius": 150, "horizon": 0.62},
  "camera": {"yaw": "bar * 45", "squash": 0.6},
  "objects": [
    {"model": "lantern.json", "count": 6,
     "x": "95 * cos(tau * i / n)", "y": "95 * sin(tau * i / n)",
     "yaw": "b * 30", "z": "5 * bounce(b)", "gap": "1 + 0.4 * pulse(b)", "outline": "#141428"}
  ]
}
```

### 全体の設定

| 項目 | 意味 | 既定 |
|---|---|---|
| `width`, `height`, `fps` | 出力の大きさとフレームレート | 1920, 1080, 24 |
| `pixel_scale` | 1ドットを出力の何px にするか。内部の画面は `width / pixel_scale` ドット幅 | 4 |
| `bpm`, `offset`, `beats_per_bar` | テンポ、拍0までの秒数（曲頭の無音）、1小節の拍数 | 120, 0, 4 |
| `duration` または `beats` | 尺（秒）または拍数 | 16拍 |
| `anim_fps` | 動きのコマ数。12 で2コマ打ち、8 で3コマ打ち。省くと毎フレーム動く | なし |
| `yaw_steps` | 回転を N 方向に丸める（16 や 32 でレトロな見た目） | なし |
| `background` | `"transparent"`、色、または `{"gradient": [上, 下]}` | transparent |
| `floor` | 市松模様の床。`size`（マスの大きさ）, `colors` [a, b], `radius`（円形に切る）, `horizon`（床の中心の高さ。画面の高さに対する割合。物体の原点もここ） | なし |

位置と大きさの単位はすべて内部のドット。1920×1080・`pixel_scale` 6 なら画面は 320×180 ドット。

### カメラ

`yaw`（世界全体の回転、度）, `x`, `y`（注視点）, `zoom`, `squash`（地面の縦つぶし。小さいほど横から見た感じ）。どれも式で動かせる。
カメラを回すと、床・物体の位置・物体の向きがまとめて回る。物体だけをその場で回すなら物体の `yaw`。

### 物体

| 項目 | 意味 | 既定 |
|---|---|---|
| `model` | モデルのファイル（シーンの JSON からの相対パス） | 必須 |
| `x`, `y`, `z` | 地面上の位置（原点は画面中央）、`z` は高さ（跳ねる動きに使う） | 0 |
| `yaw` | 向き（度） | 0 |
| `scale` | 拡大率。整数だとドットが揃う | 1 |
| `gap` | スライスの間隔（ドット）。拍で伸び縮みさせると弾む | 1 |
| `squash` | この物体だけカメラと違うつぶし率にする | カメラの値 |
| `opacity`, `visible` | 不透明度（0〜1）、表示するか（0 で消す） | 1 |
| `beats` / `time` | [開始, 終了]。その拍・秒の間だけ出す | 常に |
| `count` | 同じ物体を N 個置く。式の中で `i`（0 から）と `n`（個数）が使える | 1 |
| `outline` | 輪郭線の色 | なし |
| `shade` | 下のスライスを暗くする強さ（0〜1） | 0.2 |
| `wall` | 側面（真上にボクセルがある画素）を暗くする強さ | 0.18 |
| `shadow` | 地面の影の濃さ（0 で無し） | 0.3 |
| `pivot` | 回転軸 [x, y]（モデル内の座標） | 中心 |

`x` `y` `z` `yaw` `scale` `gap` `squash` `opacity` `visible` とカメラの各項目は、数値・式・キーフレームのどれでも書ける。

### 式で使える変数と関数

変数：`t`（秒）, `b`（拍。`offset` の時点が 0）, `bar`（小節）, `i`, `n`（`count` を使ったとき）

| 関数 | 動き |
|---|---|
| `pulse(x, k=4)` | x が整数になる瞬間に 1、そこから減衰。`pulse(b)` で毎拍のキック、`pulse(b / 2)` で2拍ごと、`pulse(b + 0.5)` で裏拍 |
| `bounce(x)` | x が1進むごとに1回跳ねる（0→1→0）。`z` に使う |
| `tri(x)` | 0→1→0 の三角波 |
| `step(x, n=1)` | 値を段階にする。`step(b) * 45` で拍ごとに 45° ずつカクッと回る |
| `ramp(x, a, b)` | a より前は 0、b より後は 1、間は直線。登場・退場に：`"scale": "ramp(b, 0, 1)"` |
| `smooth(x)` | 0〜1 をなめらかにする（`smooth(ramp(b, 0, 2))`） |
| `noise(x, seed=0)` | −1〜1 のゆらぎ。カメラの揺れに |
| `rand(seed)` | 0〜1 の固定の乱数。`rand(i)` で個体差 |
| `sin` `cos` `abs` `min` `max` `floor` `frac` `sqrt` `pow` `exp` `clamp(x, a, b)` `lerp(a, b, f)` と定数 `pi` `tau` | |

条件は `"1 if b >= 8 else 0"` のように書ける。式で使えるのは上の変数・関数と四則演算・比較だけ。

### キーフレーム

```json
"yaw": {"keys": [[0, 0], [8, 90], [16, 90], [24, 360]], "unit": "beat", "ease": "smooth"}
```

`unit` は `beat`（既定）か `sec`、`ease` は `smooth`（既定）・`linear`・`hold`。曲の構成に合わせた場面転換は、式よりこちらが書きやすい。
場面ごとに物体を入れ替えるなら、物体の `beats: [開始, 終了]` を使う。

---

## composite の層の指定

`SS composite -o out.mp4 --fps 24 [--bg 色] [--audio 曲] [--size WxH] [--duration 秒] 層…`（下から上の順）

層に書けるもの：動画ファイル（透過 `.mov` 可）／静止画／連番 PNG の入ったフォルダ／`ZIP のパス:フォルダ名`（ZIP 内のフォルダ。JIZURA の `xxx.zip:back` と `xxx.zip:front`）。

大きさは最初の層に合わせ、違う層は最近傍補間で拡大する（ドットがぼけない）。長さは一番長い層に合わせ、短い層は終わったところで消える。
