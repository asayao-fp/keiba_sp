# keiba_sp

JRA VAN DataLab / JVLink を使用した競馬予想システム

## 概要

このシステムは JRA VAN DataLab の過去レースデータを元に、ランダムフォレストで各馬の勝利確率を予測します。
JVLink が利用できない環境ではサンプルデータで動作確認が可能です。

## ディレクトリ構成

```
keiba_sp/
├── requirements.txt          # 依存ライブラリ
├── src/
│   ├── data/
│   │   ├── jvlink_loader.py  # JVLink経由のデータ取得（未接続時はサンプルデータ）
│   │   └── preprocessor.py   # データ前処理
│   ├── features/
│   │   └── engineering.py    # 特徴量エンジニアリング
│   ├── models/
│   │   └── predictor.py      # ランダムフォレスト予測モデル
│   └── predict.py            # メイン実行スクリプト
└── tests/
    └── test_predictor.py     # テストスイート
```

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

### 学習と予測をまとめて実行（デフォルト）

```bash
python -m src.predict
```

### モデルの学習のみ

```bash
python -m src.predict train --from-date 20230101 --to-date 20231231
```

### 予測のみ

```bash
python -m src.predict predict --race-id 2024XXXX
```

### JVLinkを使用する場合（Windows環境）

```bash
python -m src.predict all \
    --software-id YOUR_SOFTWARE_ID \
    --user-id YOUR_USER_ID \
    --from-date 20240101 \
    --to-date 20241231
```

### オプション一覧

| オプション | デフォルト | 説明 |
|---|---|---|
| `--from-date` | `20240101` | データ取得開始日 (YYYYMMDD) |
| `--to-date` | `20241231` | データ取得終了日 (YYYYMMDD) |
| `--software-id` | `` | JVLink ソフトウェアID |
| `--user-id` | `` | JVLink ユーザーID |
| `--model-dir` | `models` | モデル保存ディレクトリ |
| `--race-id` | *(最初のレース)* | 予測対象レースID |

## テストの実行

```bash
python -m pytest tests/ -v
```

## 予測モデルの特徴量

| 特徴量 | 説明 |
|---|---|
| `past_top3_rate` | 過去の3着以内率 |
| `jockey_win_rate` | 騎手の勝率 |
| `trainer_win_rate` | 調教師の勝率 |
| `horse_weight` | 馬体重 |
| `horse_weight_diff` | 前走比体重変化 |
| `days_since_last_race` | 前走からの間隔（日数） |
| `popularity` | 人気順 |
| `win_odds` | 単勝オッズ |
| `distance_km` | レース距離（km） |
| `track_type_enc` | 馬場種別（芝/ダート） |
| `track_condition_enc` | 馬場状態（良/稍重/重/不良） |
| `age` | 馬齢 |
| `sex_enc` | 性別（牡/牝/騸） |
| `post_position` | 枠番 |
| `odds_rank_in_race` | レース内オッズ順位 |
| `odds_norm` | レース内正規化オッズ |
| `weight_rank_in_race` | レース内馬体重順位 |
| `jockey_rank_in_race` | レース内騎手勝率順位 |
| `horses_in_race` | レース頭数 |
