"""
特徴量エンジニアリングモジュール

レースデータから予測に有効な特徴量を生成する。
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def add_race_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    同一レース内での相対特徴量を追加する。

    Parameters
    ----------
    df : pd.DataFrame
        前処理済みレースデータ

    Returns
    -------
    pd.DataFrame
        相対特徴量を追加したDataFrame
    """
    df = df.copy()

    if "race_id" not in df.columns:
        return df

    # レースごとのオッズ順位（人気の相対的な位置）
    if "win_odds" in df.columns:
        df["odds_rank_in_race"] = df.groupby("race_id")["win_odds"].rank(
            method="min", ascending=True
        )
        # オッズ正規化（レース内最大オッズで割る）
        race_max_odds = df.groupby("race_id")["win_odds"].transform("max")
        df["odds_norm"] = df["win_odds"] / race_max_odds.replace(0, np.nan).fillna(1)

    # レースごとの馬体重順位
    if "horse_weight" in df.columns:
        df["weight_rank_in_race"] = df.groupby("race_id")["horse_weight"].rank(
            method="min", ascending=False
        )

    # レースごとの騎手勝率順位
    if "jockey_win_rate" in df.columns:
        df["jockey_rank_in_race"] = df.groupby("race_id")["jockey_win_rate"].rank(
            method="min", ascending=False
        )

    # レース頭数
    df["horses_in_race"] = df.groupby("race_id")["horse_num"].transform("count")

    return df


def add_speed_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    タイム指数（速度指数）を計算して追加する。

    距離とタイムからレース内での相対速度を計算する。

    Parameters
    ----------
    df : pd.DataFrame
        レースデータ

    Returns
    -------
    pd.DataFrame
        タイム指数を追加したDataFrame
    """
    df = df.copy()

    if "finish_time_sec" not in df.columns or "distance" not in df.columns:
        return df

    # 速度 (m/s)
    df["speed_mps"] = df["distance"] / df["finish_time_sec"].replace(0, np.nan)

    # レース内での速度順位（高いほど良い）
    if "race_id" in df.columns:
        df["speed_rank_in_race"] = df.groupby("race_id")["speed_mps"].rank(
            method="min", ascending=False
        )

        # レース内平均速度との差
        race_mean_speed = df.groupby("race_id")["speed_mps"].transform("mean")
        df["speed_diff_from_mean"] = df["speed_mps"] - race_mean_speed

    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    全特徴量を構築する。

    Parameters
    ----------
    df : pd.DataFrame
        前処理済みレースデータ

    Returns
    -------
    pd.DataFrame
        特徴量を追加したDataFrame
    """
    df = add_race_relative_features(df)
    df = add_speed_index(df)
    logger.debug("特徴量構築完了: %d行 %d列", len(df), len(df.columns))
    return df


def get_engineered_feature_columns() -> list:
    """
    特徴量エンジニアリングで追加された特徴量カラム名のリストを返す。

    Returns
    -------
    list
        追加特徴量カラム名リスト
    """
    return [
        "odds_rank_in_race",
        "odds_norm",
        "weight_rank_in_race",
        "jockey_rank_in_race",
        "horses_in_race",
    ]
