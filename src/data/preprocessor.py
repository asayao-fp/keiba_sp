"""
データ前処理モジュール

JVLinkから取得した生データを機械学習モデルに入力できる形式に変換する。
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# カテゴリ変数の定義
TRACK_TYPE_MAP = {"芝": 0, "ダート": 1, "障害": 2}
TRACK_CONDITION_MAP = {"良": 0, "稍重": 1, "重": 2, "不良": 3}
SEX_MAP = {"牡": 0, "牝": 1, "騸": 2}


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    レースデータを前処理する。

    Parameters
    ----------
    df : pd.DataFrame
        生レースデータ

    Returns
    -------
    pd.DataFrame
        前処理済みDataFrame
    """
    df = df.copy()

    # カテゴリ変数をエンコード
    df["track_type_enc"] = df["track_type"].map(TRACK_TYPE_MAP).fillna(-1).astype(int)
    df["track_condition_enc"] = (
        df["track_condition"].map(TRACK_CONDITION_MAP).fillna(-1).astype(int)
    )
    df["sex_enc"] = df["sex"].map(SEX_MAP).fillna(-1).astype(int)

    # 欠損値の補完
    numeric_cols = [
        "horse_weight",
        "horse_weight_diff",
        "age",
        "days_since_last_race",
        "past_top3_rate",
        "jockey_win_rate",
        "trainer_win_rate",
        "win_odds",
        "popularity",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    # 距離をキロメートル単位に正規化
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000.0

    # 1着かどうかのラベル (目的変数)
    if "finish_position" in df.columns:
        df["is_win"] = (df["finish_position"] == 1).astype(int)

    # 3着以内かどうかのラベル
    if "finish_position" in df.columns:
        df["is_top3"] = (df["finish_position"] <= 3).astype(int)

    logger.debug("前処理完了: %d行 %d列", len(df), len(df.columns))
    return df


def get_feature_columns() -> list:
    """
    予測に使用する特徴量カラム名のリストを返す。

    Returns
    -------
    list
        特徴量カラム名リスト
    """
    return [
        "horse_weight",
        "horse_weight_diff",
        "age",
        "sex_enc",
        "post_position",
        "distance_km",
        "track_type_enc",
        "track_condition_enc",
        "days_since_last_race",
        "past_top3_rate",
        "jockey_win_rate",
        "trainer_win_rate",
        "popularity",
    ]


def get_target_column() -> str:
    """
    目的変数カラム名を返す。

    Returns
    -------
    str
        目的変数カラム名
    """
    return "is_win"
