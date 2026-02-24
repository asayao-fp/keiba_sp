"""
競馬予想メインスクリプト

使い方:
    # モデルの学習
    python -m src.predict train

    # 最新レースの予測
    python -m src.predict predict --race-id 2024XXXX

    # 学習と予測を両方実行
    python -m src.predict all
"""

import argparse
import logging
import sys

import pandas as pd

from src.data.jvlink_loader import load_data
from src.data.preprocessor import preprocess
from src.features.engineering import build_features
from src.models.predictor import HorseRacePredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_DIR = "models"


def run_train(args) -> None:
    """モデルを学習する。"""
    logger.info("データを読み込み中... (%s 〜 %s)", args.from_date, args.to_date)
    raw_df = load_data(
        from_date=args.from_date,
        to_date=args.to_date,
        software_id=args.software_id,
        user_id=args.user_id,
    )
    logger.info("読み込み完了: %d件", len(raw_df))

    df = preprocess(raw_df)
    df = build_features(df)

    predictor = HorseRacePredictor(model_dir=args.model_dir)
    result = predictor.train(df)

    logger.info("学習結果:")
    logger.info("  CV ROC-AUC: %.4f ± %.4f", result["cv_roc_auc_mean"], result["cv_roc_auc_std"])
    logger.info("  サンプル数: %d", result["n_samples"])
    logger.info("  特徴量数: %d", result["n_features"])

    predictor.save(args.model_dir)
    logger.info("モデルを保存しました: %s", args.model_dir)

    logger.info("\n特徴量重要度（上位10件）:")
    importances = predictor.get_feature_importances()
    for feature, importance in importances.head(10).items():
        logger.info("  %-35s %.4f", feature, importance)


def run_predict(args) -> None:
    """指定レースの予測を行う。"""
    logger.info("データを読み込み中...")
    raw_df = load_data(
        from_date=args.from_date,
        to_date=args.to_date,
        software_id=args.software_id,
        user_id=args.user_id,
    )

    df = preprocess(raw_df)
    df = build_features(df)

    predictor = HorseRacePredictor(model_dir=args.model_dir)
    try:
        predictor.load(args.model_dir)
    except FileNotFoundError:
        logger.warning("保存済みモデルが見つかりません。データを使って学習します。")
        predictor.train(df)
        predictor.save(args.model_dir)

    # レースIDが指定されている場合は絞り込む
    if args.race_id:
        if "race_id" not in df.columns:
            logger.error("データにrace_idカラムがありません")
            sys.exit(1)
        race_df = df[df["race_id"] == args.race_id]
        if race_df.empty:
            logger.error("race_id '%s' が見つかりません", args.race_id)
            sys.exit(1)
        _print_prediction(predictor, race_df, args.race_id)
    else:
        # 最初のレースを対象にする
        race_ids = df["race_id"].unique() if "race_id" in df.columns else []
        if len(race_ids) == 0:
            logger.error("予測対象レースが見つかりません")
            sys.exit(1)
        first_race_id = race_ids[0]
        race_df = df[df["race_id"] == first_race_id]
        _print_prediction(predictor, race_df, first_race_id)


def _print_prediction(
    predictor: HorseRacePredictor, race_df: pd.DataFrame, race_id: str
) -> None:
    """予測結果を表示する。"""
    result = predictor.predict_race(race_df)

    display_cols = ["horse_num", "win_probability", "prediction_rank"]
    optional_cols = ["horse_name", "jockey_id", "win_odds", "popularity"]
    for col in optional_cols:
        if col in result.columns:
            display_cols.insert(2, col)

    print(f"\n{'='*60}")
    print(f"レースID: {race_id}  予測結果（勝利確率順）")
    print(f"{'='*60}")
    print(result[display_cols].to_string(index=False))
    print(f"{'='*60}")
    print(f"\n◎本命: 馬番{result.iloc[0]['horse_num']} (勝利確率: {result.iloc[0]['win_probability']:.1%})")
    if len(result) >= 2:
        print(f"○対抗: 馬番{result.iloc[1]['horse_num']} (勝利確率: {result.iloc[1]['win_probability']:.1%})")
    if len(result) >= 3:
        print(f"▲単穴: 馬番{result.iloc[2]['horse_num']} (勝利確率: {result.iloc[2]['win_probability']:.1%})")


def run_all(args) -> None:
    """学習と予測を両方実行する。"""
    run_train(args)
    run_predict(args)


def main() -> None:
    """エントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="競馬予想システム - JRA VAN DataLab / JVLink使用"
    )
    parser.add_argument(
        "--from-date",
        default="20240101",
        help="データ取得開始日 (YYYYMMDD形式, デフォルト: 20240101)",
    )
    parser.add_argument(
        "--to-date",
        default="20241231",
        help="データ取得終了日 (YYYYMMDD形式, デフォルト: 20241231)",
    )
    parser.add_argument(
        "--software-id",
        default="",
        help="JVLinkソフトウェアID",
    )
    parser.add_argument(
        "--user-id",
        default="",
        help="JVLinkユーザーID",
    )
    parser.add_argument(
        "--model-dir",
        default=MODEL_DIR,
        help=f"モデル保存ディレクトリ (デフォルト: {MODEL_DIR})",
    )
    parser.add_argument(
        "--race-id",
        default=None,
        help="予測対象レースID",
    )

    subparsers = parser.add_subparsers(dest="command", help="実行コマンド")
    subparsers.add_parser("train", help="モデルの学習")
    subparsers.add_parser("predict", help="レース予測")
    subparsers.add_parser("all", help="学習と予測を両方実行")

    args = parser.parse_args()

    if args.command == "train":
        run_train(args)
    elif args.command == "predict":
        run_predict(args)
    elif args.command == "all":
        run_all(args)
    else:
        # デフォルトは学習＋予測
        run_all(args)


if __name__ == "__main__":
    main()
