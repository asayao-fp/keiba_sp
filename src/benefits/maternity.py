"""
出産・育休・扶養に関する給付金・控除計算モジュール

対象給付金・控除:
  - 出産一時金      : 健康保険から支給される一時金
  - 出産手当金      : 産休中に健康保険から支給される手当
  - 育児休業給付金  : 育休中に雇用保険から支給される給付金
  - 扶養控除        : 所得税・住民税の扶養控除
  - 配偶者控除      : 所得税・住民税の配偶者控除
"""

# ---------------------------------------------------------------------------
# 出産一時金 (Childbirth lump-sum payment)
# ---------------------------------------------------------------------------

# 2023年4月以降の出産育児一時金 (単位: 円)
CHILDBIRTH_LUMP_SUM = 500_000


def calculate_childbirth_lump_sum() -> int:
    """
    出産育児一時金を返す。

    健康保険（または国民健康保険）の被保険者・被扶養者が出産した場合に
    1児につき支給される一時金。2023年4月以降は 50万円。

    Returns
    -------
    int
        出産育児一時金 (円)
    """
    return CHILDBIRTH_LUMP_SUM


# ---------------------------------------------------------------------------
# 出産手当金 (Maternity benefit)
# ---------------------------------------------------------------------------

# 産前休業日数 (出産予定日以前42日 = 6週間)
MATERNITY_LEAVE_DAYS_BEFORE = 42
# 産後休業日数 (出産日翌日から56日 = 8週間)
MATERNITY_LEAVE_DAYS_AFTER = 56
# 産休合計日数
MATERNITY_LEAVE_DAYS_TOTAL = MATERNITY_LEAVE_DAYS_BEFORE + MATERNITY_LEAVE_DAYS_AFTER


def calculate_maternity_benefit(
    monthly_standard_remuneration: int,
    days: int = MATERNITY_LEAVE_DAYS_TOTAL,
) -> float:
    """
    出産手当金を計算する。

    健康保険の被保険者（本人）が産休を取得した場合に支給される手当。
    支給額 = 標準報酬月額 ÷ 30 × 2/3 × 対象日数

    Parameters
    ----------
    monthly_standard_remuneration : int
        標準報酬月額 (円)。直近12ヶ月の標準報酬月額の平均が基準となる。
    days : int, optional
        産休取得日数。デフォルトは産前42日＋産後56日の合計98日。

    Returns
    -------
    float
        出産手当金の合計額 (円)

    Raises
    ------
    ValueError
        monthly_standard_remuneration または days が負の場合。
    """
    if monthly_standard_remuneration < 0:
        raise ValueError("標準報酬月額は0以上を指定してください。")
    if days < 0:
        raise ValueError("産休日数は0以上を指定してください。")

    daily_amount = monthly_standard_remuneration / 30 * (2 / 3)
    return daily_amount * days


# ---------------------------------------------------------------------------
# 育児休業給付金 (Childcare leave benefit)
# ---------------------------------------------------------------------------

# 育休開始から180日間の給付率
CHILDCARE_LEAVE_RATE_FIRST = 0.67
# 180日経過後の給付率
CHILDCARE_LEAVE_RATE_AFTER = 0.50
# 給付率が切り替わる日数
CHILDCARE_LEAVE_THRESHOLD_DAYS = 180


def calculate_childcare_leave_benefit(
    monthly_wage: int,
    leave_days: int = 365,
) -> dict:
    """
    育児休業給付金を計算する。

    雇用保険の被保険者が育休を取得した場合に支給される給付金。
    - 育休開始から180日間: 休業開始時賃金日額 × 67%
    - 181日目以降        : 休業開始時賃金日額 × 50%

    賃金日額 = 月額賃金 × 12 ÷ 365 として計算する。

    Parameters
    ----------
    monthly_wage : int
        月額賃金 (円)。育休前6ヶ月の平均月額賃金を入力する。
    leave_days : int, optional
        育休取得日数。デフォルトは365日（約1年）。

    Returns
    -------
    dict
        以下のキーを含む辞書:
        - ``first_period_days``   : 高率期間の日数 (最大180日)
        - ``second_period_days``  : 低率期間の日数
        - ``first_period_amount`` : 高率期間の給付金 (円)
        - ``second_period_amount``: 低率期間の給付金 (円)
        - ``total``               : 合計給付金 (円)

    Raises
    ------
    ValueError
        monthly_wage または leave_days が負の場合。
    """
    if monthly_wage < 0:
        raise ValueError("月額賃金は0以上を指定してください。")
    if leave_days < 0:
        raise ValueError("育休取得日数は0以上を指定してください。")

    daily_wage = monthly_wage * 12 / 365

    first_days = min(leave_days, CHILDCARE_LEAVE_THRESHOLD_DAYS)
    second_days = max(leave_days - CHILDCARE_LEAVE_THRESHOLD_DAYS, 0)

    first_amount = daily_wage * CHILDCARE_LEAVE_RATE_FIRST * first_days
    second_amount = daily_wage * CHILDCARE_LEAVE_RATE_AFTER * second_days

    return {
        "first_period_days": first_days,
        "second_period_days": second_days,
        "first_period_amount": first_amount,
        "second_period_amount": second_amount,
        "total": first_amount + second_amount,
    }


# ---------------------------------------------------------------------------
# 扶養控除 (Dependent deduction)
# ---------------------------------------------------------------------------

# 一般の控除対象扶養親族 (16歳以上、19歳未満 or 23歳以上70歳未満)
DEPENDENT_DEDUCTION_GENERAL = 380_000
# 特定扶養親族 (19歳以上23歳未満)
DEPENDENT_DEDUCTION_SPECIFIED = 630_000
# 老人扶養親族 同居 (70歳以上 かつ 同居老親等)
DEPENDENT_DEDUCTION_ELDERLY_CORESIDENT = 580_000
# 老人扶養親族 別居 (70歳以上 かつ 同居老親等以外)
DEPENDENT_DEDUCTION_ELDERLY_SEPARATE = 480_000


def calculate_dependent_deduction(age: int, is_coresident_elderly: bool = False) -> int:
    """
    扶養控除額を計算する (所得税)。

    16歳未満の扶養親族には扶養控除が適用されない（年少扶養親族）。

    Parameters
    ----------
    age : int
        扶養親族の年齢。
    is_coresident_elderly : bool, optional
        70歳以上の場合に、同居老親等かどうか。デフォルトは False (別居)。

    Returns
    -------
    int
        扶養控除額 (円)。控除対象外の場合は 0。

    Raises
    ------
    ValueError
        age が負の場合。
    """
    if age < 0:
        raise ValueError("年齢は0以上を指定してください。")

    if age < 16:
        return 0
    if age >= 70:
        return (
            DEPENDENT_DEDUCTION_ELDERLY_CORESIDENT
            if is_coresident_elderly
            else DEPENDENT_DEDUCTION_ELDERLY_SEPARATE
        )
    if 19 <= age < 23:
        return DEPENDENT_DEDUCTION_SPECIFIED
    return DEPENDENT_DEDUCTION_GENERAL


# ---------------------------------------------------------------------------
# 配偶者控除 / 配偶者特別控除 (Spouse deduction)
# ---------------------------------------------------------------------------

def calculate_spouse_deduction(
    taxpayer_income: int,
    spouse_income: int,
) -> int:
    """
    配偶者控除または配偶者特別控除の金額を計算する (所得税)。

    配偶者控除: 配偶者の合計所得金額が48万円以下の場合に適用。
    配偶者特別控除: 配偶者の合計所得金額が48万円超133万円以下の場合に適用。

    Parameters
    ----------
    taxpayer_income : int
        納税者本人の合計所得金額 (円)。
        1,000万円超の場合は配偶者控除・配偶者特別控除ともに適用不可。
    spouse_income : int
        配偶者の合計所得金額 (円)。

    Returns
    -------
    int
        控除額 (円)。適用外の場合は 0。

    Raises
    ------
    ValueError
        taxpayer_income または spouse_income が負の場合。

    Notes
    -----
    ここでの「所得金額」は給与収入ではなく、給与所得控除後の所得金額を指す。
    給与収入から所得金額への換算は別途行う必要がある。
    """
    if taxpayer_income < 0:
        raise ValueError("納税者の所得金額は0以上を指定してください。")
    if spouse_income < 0:
        raise ValueError("配偶者の所得金額は0以上を指定してください。")

    # 納税者所得が1,000万円超 → 控除不可
    if taxpayer_income > 10_000_000:
        return 0

    # 配偶者控除 (配偶者所得 48万円以下)
    if spouse_income <= 480_000:
        if taxpayer_income <= 9_000_000:
            return 380_000
        if taxpayer_income <= 9_500_000:
            return 260_000
        return 130_000

    # 配偶者特別控除 (配偶者所得 48万円超 133万円以下)
    if spouse_income <= 1_330_000:
        return _spouse_special_deduction(taxpayer_income, spouse_income)

    return 0


def _spouse_special_deduction(taxpayer_income: int, spouse_income: int) -> int:
    """配偶者特別控除額を返す (内部関数)。"""
    # 配偶者所得金額に応じた控除額テーブル (納税者所得 900万円以下の場合)
    # (所得下限, 所得上限, 控除額)
    _brackets_900 = [
        (480_001,   950_000, 380_000),
        (950_001, 1_000_000, 360_000),
        (1_000_001, 1_050_000, 310_000),
        (1_050_001, 1_100_000, 260_000),
        (1_100_001, 1_150_000, 210_000),
        (1_150_001, 1_200_000, 160_000),
        (1_200_001, 1_250_000, 110_000),
        (1_250_001, 1_300_000,  60_000),
        (1_300_001, 1_330_000,  30_000),
    ]
    # 納税者所得 900万円超 950万円以下
    _brackets_950 = [
        (480_001,   950_000, 260_000),
        (950_001, 1_000_000, 240_000),
        (1_000_001, 1_050_000, 210_000),
        (1_050_001, 1_100_000, 180_000),
        (1_100_001, 1_150_000, 140_000),
        (1_150_001, 1_200_000, 110_000),
        (1_200_001, 1_250_000,  80_000),
        (1_250_001, 1_300_000,  40_000),
        (1_300_001, 1_330_000,  20_000),
    ]
    # 納税者所得 950万円超 1,000万円以下
    _brackets_1000 = [
        (480_001,   950_000, 130_000),
        (950_001, 1_000_000, 120_000),
        (1_000_001, 1_050_000, 110_000),
        (1_050_001, 1_100_000,  90_000),
        (1_100_001, 1_150_000,  70_000),
        (1_150_001, 1_200_000,  60_000),
        (1_200_001, 1_250_000,  40_000),
        (1_250_001, 1_300_000,  20_000),
        (1_300_001, 1_330_000,  10_000),
    ]

    if taxpayer_income <= 9_000_000:
        brackets = _brackets_900
    elif taxpayer_income <= 9_500_000:
        brackets = _brackets_950
    else:
        brackets = _brackets_1000

    for low, high, deduction in brackets:
        if low <= spouse_income <= high:
            return deduction
    return 0
