"""
ランダムフォレストによる競馬予測モデル
"""

import logging
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.data.preprocessor import get_feature_columns, get_target_column
from src.features.engineering import get_engineered_feature_columns

logger = logging.getLogger(__name__)

_MODEL_FILENAME = "horse_race_predictor.joblib"


def _all_feature_columns() -> list:
    """基本特徴量とエンジニアリング特徴量を結合したリストを返す。"""
    return get_feature_columns() + get_engineered_feature_columns()


class HorseRacePredictor:
    """ランダムフォレストを使った競馬勝利確率予測モデル。"""

    def __init__(self, model_dir: str = "models", n_estimators: int = 200, random_state: int = 42):
        self.model_dir = model_dir
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._model: RandomForestClassifier | None = None
        self._feature_cols: list[str] = []

    def _select_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameから利用可能な特徴量カラムを選択する。"""
        candidates = _all_feature_columns()
        cols = [c for c in candidates if c in df.columns]
        return df[cols]

    def train(self, df: pd.DataFrame) -> dict:
        """
        モデルを学習する。

        Parameters
        ----------
        df : pd.DataFrame
            特徴量エンジニアリング済みのレースデータ

        Returns
        -------
        dict
            学習結果 (cv_roc_auc_mean, cv_roc_auc_std, n_samples, n_features)
        """
        target_col = get_target_column()
        X = self._select_features(df)
        y = df[target_col]
        self._feature_cols = X.columns.tolist()

        self._model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        scores = cross_val_score(self._model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)

        self._model.fit(X, y)

        result = {
            "cv_roc_auc_mean": float(scores.mean()),
            "cv_roc_auc_std": float(scores.std()),
            "n_samples": len(df),
            "n_features": len(self._feature_cols),
        }
        logger.info(
            "学習完了: CV ROC-AUC = %.4f ± %.4f",
            result["cv_roc_auc_mean"],
            result["cv_roc_auc_std"],
        )
        return result

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """
        勝利確率を予測する。

        Parameters
        ----------
        df : pd.DataFrame
            特徴量エンジニアリング済みのレースデータ

        Returns
        -------
        np.ndarray
            各行の勝利確率
        """
        if self._model is None:
            raise RuntimeError("モデルが学習されていません。train() を先に呼び出してください。")
        X = df[[c for c in self._feature_cols if c in df.columns]]
        return self._model.predict_proba(X)[:, 1]

    def predict_race(self, race_df: pd.DataFrame) -> pd.DataFrame:
        """
        1レース分の予測を行い、勝利確率順に並べた結果を返す。

        Parameters
        ----------
        race_df : pd.DataFrame
            対象レースのデータ (1レース分)

        Returns
        -------
        pd.DataFrame
            win_probability と prediction_rank を追加したDataFrame (確率降順)
        """
        result = race_df.copy()
        result["win_probability"] = self.predict_proba(race_df)
        result = result.sort_values("win_probability", ascending=False).reset_index(drop=True)
        result["prediction_rank"] = range(1, len(result) + 1)
        return result

    def get_feature_importances(self) -> pd.Series:
        """
        特徴量重要度を降順ソートして返す。

        Returns
        -------
        pd.Series
            特徴量重要度 (降順)
        """
        if self._model is None:
            raise RuntimeError("モデルが学習されていません。train() を先に呼び出してください。")
        importances = pd.Series(
            self._model.feature_importances_, index=self._feature_cols
        )
        return importances.sort_values(ascending=False)

    def save(self, model_dir: str | None = None) -> None:
        """
        モデルをファイルに保存する。

        Parameters
        ----------
        model_dir : str, optional
            保存先ディレクトリ。省略時はインスタンスの model_dir を使用。
        """
        if self._model is None:
            raise RuntimeError("保存するモデルがありません。train() を先に呼び出してください。")
        save_dir = Path(model_dir or self.model_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / _MODEL_FILENAME
        joblib.dump({"model": self._model, "feature_cols": self._feature_cols}, path)
        logger.info("モデルを保存しました: %s", path)

    def load(self, model_dir: str | None = None) -> None:
        """
        保存済みモデルをファイルから読み込む。

        Parameters
        ----------
        model_dir : str, optional
            読み込み元ディレクトリ。省略時はインスタンスの model_dir を使用。
        """
        load_dir = Path(model_dir or self.model_dir)
        path = load_dir / _MODEL_FILENAME
        if not path.exists():
            raise FileNotFoundError(f"モデルファイルが見つかりません: {path}")
        data = joblib.load(path)
        self._model = data["model"]
        self._feature_cols = data["feature_cols"]
        logger.info("モデルを読み込みました: %s", path)
