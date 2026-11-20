# ドラムレギオン 紹介サイト

リズム進軍アクション「ドラムレギオン」の紹介ページです。画面に出てくる立体（王・兵・敵・城・太鼓・木）は、3D モデルではなく
**スプライトスタッキング**（輪切りにしたドット絵を 1 ドットずつずらして積み、全部を同じ角度で回す）で描いています。

- React + Vite + Tailwind CSS、動きは [motion](https://motion.dev/)（旧 framer-motion）
- 立体の描画は `src/stack/engine.ts`（2D キャンバス。小さく描いて、ぼかさずに拡大）
- 拍の時計と音は `src/lib/beat.ts`（120 BPM。音は「太鼓を鳴らす」を押したときだけ鳴ります）

## 動かす

```sh
npm install
npm run dev      # 開発サーバー
npm run build    # 型検査 + ビルド（dist/）
npm run preview  # ビルド結果の確認
```

「出陣する」ボタンのリンク先は、ビルド時の環境変数 `VITE_GAME_URL` で指定します（未指定ではゲームのリポジトリを開きます）。

```sh
VITE_GAME_URL=https://example.com/drum-legion/ npm run build
```

## 立体の素材を作り直す

`public/stacks/*.png`（スライスシート）と `src/stacks.json` は、`tools/build_models.py` が作ります。
キャラクターはゲーム本体（bokosuka_war_awaken の `src/game/sprites.ts`）の 16×16 のドット絵を写して、厚みのある人形にしています。
城や太鼓などは箱・円柱・回転体の組み合わせです。描画の確認には、このリポジトリの `sprite-stack-mv` スキルのレンダラーを使っています。

```sh
python3 tools/build_models.py --preview check.png   # Pillow と numpy が必要
```

ゲーム側の絵を変えたときは、`tools/build_models.py` の中の絵も同じように直してください（自動では同期しません）。

## 構成

| セクション | ファイル | 見どころ |
|---|---|---|
| ヒーロー | `src/sections/Hero.tsx` | 戦場全体が拍で跳ねる。ドラッグ・スクロールで回る |
| 拍を叩く | `src/sections/TapGame.tsx` | 拍に合わせて叩くと先頭の敵が倒れる（輪切りが飛び散る） |
| 描き方 | `src/sections/Anatomy.tsx` | スクロールで城が輪切りに分かれ、積み直され、回る |
| 軍・敵 | `src/sections/Roster.tsx` | 傾くカードと、ポインターを追って回る人形 |
| ルール・締め | `src/sections/Closing.tsx` | 連鎖の数字、こちらへ進んでくる軍 |

動きを減らす設定（`prefers-reduced-motion`）の環境では、キャンバスの更新を 0.5 秒に 1 回に落とし、motion の移動・回転を止めます。
