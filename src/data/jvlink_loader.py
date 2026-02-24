"""
JVLink / JRA VAN DataLab データローダー

JVLinkが利用可能な場合はCOM経由でデータを取得し、
利用できない場合はCSVファイルからデータを読み込みます。
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# JVLinkのCOMオブジェクト定数
JVLINK_DATASPEC_RACE = "RACE"
JVLINK_DATASPEC_DIFF = "DIFF"
JVLINK_REALTIMEOPEN_NORMAL = 1
JVLINK_OPEN_NORMAL = 1


def _is_jvlink_available() -> bool:
    """JVLinkが利用可能かどうかを確認する。"""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


class JVLinkLoader:
    """JVLink経由でJRA VANデータを読み込むクラス。"""

    def __init__(self, software_id: str = "", user_id: str = ""):
        self.software_id = software_id
        self.user_id = user_id
        self._jvlink = None
        self._available = _is_jvlink_available()

    def _get_jvlink(self):
        """JVLinkのCOMオブジェクトを取得する。"""
        if self._jvlink is None:
            import win32com.client
            self._jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
            self._jvlink.JVInit(self.software_id)
        return self._jvlink

    def load_race_results(self, from_date: str, to_date: str) -> pd.DataFrame:
        """
        指定期間のレース結果を取得する。

        Parameters
        ----------
        from_date : str
            開始日 (YYYYMMDD形式)
        to_date : str
            終了日 (YYYYMMDD形式)

        Returns
        -------
        pd.DataFrame
            レース結果のDataFrame
        """
        if not self._available:
            logger.warning(
                "JVLinkが利用できません。サンプルデータを使用します。"
            )
            return _generate_sample_race_results()

        try:
            jv = self._get_jvlink()
            ret = jv.JVOpen(
                JVLINK_DATASPEC_RACE,
                from_date + "000000",
                JVLINK_OPEN_NORMAL,
                0,
                0,
                "",
            )
            if ret != 0:
                raise RuntimeError(f"JVOpen failed: {ret}")

            records = []
            while True:
                buff, nSize, szFileName = "", 0, ""
                ret, buff, nSize, szFileName = jv.JVRead(buff, nSize, szFileName)
                if ret == 0:
                    break
                if ret < 0:
                    raise RuntimeError(f"JVRead failed: {ret}")
                parsed = _parse_race_record(buff)
                if parsed:
                    records.extend(parsed)

            jv.JVClose()
            return pd.DataFrame(records)
        except Exception as exc:
            logger.error("JVLinkからのデータ取得に失敗しました: %s", exc)
            raise

    def is_available(self) -> bool:
        """JVLinkが利用可能かどうかを返す。"""
        return self._available


def _parse_race_record(buff: str) -> list:
    """JVLinkのバイナリレコードをパースする（簡易実装）。"""
    # JVLinkのレコードフォーマットに基づくパース処理
    # 実際の実装ではJVLinkのSDKドキュメントに従ってフィールドを抽出する
    if not buff or len(buff) < 10:
        return []
    # ここでは簡易的に空リストを返す（実環境では適切にパースする）
    return []


def _generate_sample_race_results() -> pd.DataFrame:
    """
    テスト・開発用のサンプルレースデータを生成する。

    Returns
    -------
    pd.DataFrame
        サンプルのレース結果DataFrame
    """
    rng = np.random.default_rng(42)
    n_races = 100
    horses_per_race = 16
    records = []

    for race_id in range(1, n_races + 1):
        n_horses = rng.integers(8, horses_per_race + 1)
        finish_order = rng.permutation(n_horses) + 1

        for horse_num in range(1, n_horses + 1):
            records.append(
                {
                    "race_id": f"2024{race_id:04d}",
                    "horse_num": horse_num,
                    "horse_id": f"H{rng.integers(1000, 9999):04d}",
                    "horse_name": f"テスト馬{rng.integers(1, 1000):03d}",
                    "jockey_id": f"J{rng.integers(1, 50):02d}",
                    "trainer_id": f"T{rng.integers(1, 100):03d}",
                    "horse_weight": int(rng.integers(420, 560)),
                    "horse_weight_diff": int(rng.integers(-10, 11)),
                    "age": int(rng.integers(2, 8)),
                    "sex": rng.choice(["牡", "牝", "騸"]),
                    "post_position": horse_num,
                    "distance": rng.choice([1000, 1200, 1400, 1600, 1800, 2000, 2400]),
                    "track_type": rng.choice(["芝", "ダート"]),
                    "track_condition": rng.choice(["良", "稍重", "重", "不良"]),
                    "finish_time_sec": round(float(rng.uniform(60, 160)), 1),
                    "finish_position": int(finish_order[horse_num - 1]),
                    "win_odds": round(float(rng.uniform(1.1, 99.9)), 1),
                    "popularity": int(rng.integers(1, n_horses + 1)),
                    "days_since_last_race": int(rng.integers(7, 180)),
                    "past_top3_rate": round(float(rng.uniform(0, 1)), 3),
                    "jockey_win_rate": round(float(rng.uniform(0, 0.3)), 3),
                    "trainer_win_rate": round(float(rng.uniform(0, 0.3)), 3),
                    "race_date": f"2024{race_id // 10 + 1:02d}{(race_id % 28) + 1:02d}",
                    "venue_code": rng.choice(["01", "02", "03", "04", "05", "06"]),
                }
            )

    return pd.DataFrame(records)


def load_data(
    from_date: str = "20240101",
    to_date: str = "20241231",
    software_id: str = "",
    user_id: str = "",
) -> pd.DataFrame:
    """
    レースデータを読み込む。

    JVLinkが利用可能な場合はJVLink経由で取得し、
    利用できない場合はサンプルデータを返す。

    Parameters
    ----------
    from_date : str
        開始日 (YYYYMMDD形式)
    to_date : str
        終了日 (YYYYMMDD形式)
    software_id : str
        JVLinkソフトウェアID
    user_id : str
        JVLinkユーザーID

    Returns
    -------
    pd.DataFrame
        レースデータ
    """
    loader = JVLinkLoader(software_id=software_id, user_id=user_id)
    return loader.load_race_results(from_date, to_date)
