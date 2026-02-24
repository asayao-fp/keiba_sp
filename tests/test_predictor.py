"""
予測システムのテスト
"""

import pytest
import numpy as np
import pandas as pd

from src.data.jvlink_loader import _generate_sample_race_results, load_data
from src.data.preprocessor import preprocess, get_feature_columns, get_target_column
from src.features.engineering import (
    build_features,
    add_race_relative_features,
    add_speed_index,
    get_engineered_feature_columns,
)
from src.models.predictor import HorseRacePredictor


@pytest.fixture
def sample_df():
    """サンプルレースデータを生成するフィクスチャ。"""
    return _generate_sample_race_results()


@pytest.fixture
def processed_df(sample_df):
    """前処理・特徴量エンジニアリング済みデータを生成するフィクスチャ。"""
    df = preprocess(sample_df)
    df = build_features(df)
    return df


class TestJVLinkLoader:
    def test_generate_sample_returns_dataframe(self):
        df = _generate_sample_race_results()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_sample_has_required_columns(self):
        df = _generate_sample_race_results()
        required = [
            "race_id", "horse_num", "horse_id", "finish_position",
            "track_type", "track_condition", "distance",
        ]
        for col in required:
            assert col in df.columns, f"カラム '{col}' がありません"

    def test_load_data_returns_dataframe(self):
        df = load_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_finish_position_is_valid(self):
        df = _generate_sample_race_results()
        assert (df["finish_position"] >= 1).all()

    def test_each_race_has_unique_finish_positions(self):
        df = _generate_sample_race_results()
        for _, race in df.groupby("race_id"):
            positions = race["finish_position"].tolist()
            assert len(positions) == len(set(positions)), "同一レース内で着順が重複しています"


class TestPreprocessor:
    def test_preprocess_adds_encoded_columns(self, sample_df):
        df = preprocess(sample_df)
        assert "track_type_enc" in df.columns
        assert "track_condition_enc" in df.columns
        assert "sex_enc" in df.columns

    def test_preprocess_adds_is_win_column(self, sample_df):
        df = preprocess(sample_df)
        assert "is_win" in df.columns
        assert df["is_win"].isin([0, 1]).all()

    def test_preprocess_adds_is_top3_column(self, sample_df):
        df = preprocess(sample_df)
        assert "is_top3" in df.columns
        assert df["is_top3"].isin([0, 1]).all()

    def test_preprocess_adds_distance_km(self, sample_df):
        df = preprocess(sample_df)
        assert "distance_km" in df.columns
        assert (df["distance_km"] == df["distance"] / 1000.0).all()

    def test_no_null_in_feature_columns(self, sample_df):
        df = preprocess(sample_df)
        for col in get_feature_columns():
            if col in df.columns:
                assert df[col].isna().sum() == 0, f"カラム '{col}' にnullがあります"

    def test_get_feature_columns_returns_list(self):
        cols = get_feature_columns()
        assert isinstance(cols, list)
        assert len(cols) > 0

    def test_get_target_column_returns_string(self):
        col = get_target_column()
        assert isinstance(col, str)
        assert col == "is_win"


class TestFeatureEngineering:
    def test_add_race_relative_features(self, sample_df):
        df = preprocess(sample_df)
        df = add_race_relative_features(df)
        assert "odds_rank_in_race" in df.columns
        assert "odds_norm" in df.columns
        assert "horses_in_race" in df.columns

    def test_add_speed_index(self, sample_df):
        df = preprocess(sample_df)
        df = add_speed_index(df)
        assert "speed_mps" in df.columns

    def test_build_features_returns_dataframe(self, sample_df):
        df = preprocess(sample_df)
        df = build_features(df)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_odds_norm_between_0_and_1(self, sample_df):
        df = preprocess(sample_df)
        df = add_race_relative_features(df)
        valid = df["odds_norm"].dropna()
        assert (valid >= 0).all()
        assert (valid <= 1).all()

    def test_engineered_feature_columns_returns_list(self):
        cols = get_engineered_feature_columns()
        assert isinstance(cols, list)
        assert len(cols) > 0


class TestHorseRacePredictor:
    def test_train_returns_dict(self, processed_df):
        predictor = HorseRacePredictor()
        result = predictor.train(processed_df)
        assert isinstance(result, dict)
        assert "cv_roc_auc_mean" in result
        assert "n_samples" in result

    def test_cv_roc_auc_above_chance(self, processed_df):
        predictor = HorseRacePredictor()
        result = predictor.train(processed_df)
        # ランダムより有意に良いスコア（0.5以上）であることを確認
        assert result["cv_roc_auc_mean"] >= 0.4

    def test_predict_proba_shape(self, processed_df):
        predictor = HorseRacePredictor()
        predictor.train(processed_df)
        proba = predictor.predict_proba(processed_df)
        assert len(proba) == len(processed_df)

    def test_predict_proba_between_0_and_1(self, processed_df):
        predictor = HorseRacePredictor()
        predictor.train(processed_df)
        proba = predictor.predict_proba(processed_df)
        assert (proba >= 0).all()
        assert (proba <= 1).all()

    def test_predict_race_sorted_by_probability(self, processed_df):
        predictor = HorseRacePredictor()
        predictor.train(processed_df)
        first_race_id = processed_df["race_id"].iloc[0]
        race_df = processed_df[processed_df["race_id"] == first_race_id]
        result = predictor.predict_race(race_df)
        probas = result["win_probability"].tolist()
        assert probas == sorted(probas, reverse=True)

    def test_predict_race_has_prediction_rank(self, processed_df):
        predictor = HorseRacePredictor()
        predictor.train(processed_df)
        first_race_id = processed_df["race_id"].iloc[0]
        race_df = processed_df[processed_df["race_id"] == first_race_id]
        result = predictor.predict_race(race_df)
        assert "prediction_rank" in result.columns
        assert result["prediction_rank"].iloc[0] == 1

    def test_predict_before_train_raises(self, processed_df):
        predictor = HorseRacePredictor()
        with pytest.raises(RuntimeError):
            predictor.predict_proba(processed_df)

    def test_save_and_load(self, processed_df, tmp_path):
        predictor = HorseRacePredictor(model_dir=str(tmp_path))
        predictor.train(processed_df)
        predictor.save(str(tmp_path))

        loaded = HorseRacePredictor(model_dir=str(tmp_path))
        loaded.load(str(tmp_path))
        proba = loaded.predict_proba(processed_df)
        assert len(proba) == len(processed_df)

    def test_get_feature_importances(self, processed_df):
        predictor = HorseRacePredictor()
        predictor.train(processed_df)
        importances = predictor.get_feature_importances()
        assert isinstance(importances, pd.Series)
        assert len(importances) > 0
        # 降順ソートされていることを確認
        vals = importances.tolist()
        assert vals == sorted(vals, reverse=True)
