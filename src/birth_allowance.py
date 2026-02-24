"""
出産に関する給付金・控除の計算モジュール

出産に伴う主な給付金・控除の概算を計算する。

対象の給付金・控除:
    - 出産育児一時金
    - 出産手当金（健康保険加入者のみ）
    - 育児休業給付金
    - 医療費控除（税負担軽減額）
"""

from __future__ import annotations

from dataclasses import dataclass, field


# 2023年4月以降の出産育児一時金 (円)
CHILDBIRTH_LUMP_SUM = 500_000

# 産前産後休業日数
MATERNITY_ANTE_NATAL_DAYS = 42   # 産前 42日
MATERNITY_POST_NATAL_DAYS = 56   # 産後 56日
MATERNITY_TOTAL_DAYS = MATERNITY_ANTE_NATAL_DAYS + MATERNITY_POST_NATAL_DAYS  # 98日

# 出産手当金の給付割合
MATERNITY_ALLOWANCE_RATE = 2 / 3

# 育児休業給付金の給付割合
CHILDCARE_LEAVE_RATE_FIRST = 0.67   # 最初の 180 日
CHILDCARE_LEAVE_RATE_AFTER = 0.50   # 180 日経過後
CHILDCARE_LEAVE_THRESHOLD_DAYS = 180

# 医療費控除の基準額 (円)
MEDICAL_DEDUCTION_BASE = 100_000


@dataclass
class BirthAllowanceSummary:
    """計算結果をまとめたデータクラス。"""

    childbirth_lump_sum: int
    """出産育児一時金 (円)"""

    maternity_allowance: float
    """出産手当金 (円)。健康保険加入者のみ受給可能。"""

    childcare_leave_benefit: float
    """育児休業給付金 (円)。"""

    medical_expense_deduction_relief: float
    """医療費控除による税負担軽減額の概算 (円)。"""

    childcare_leave_days: int
    """育児休業給付金の対象日数。"""

    details: dict = field(default_factory=dict)
    """各給付金の計算内訳。"""

    def total(self) -> float:
        """受取総額（税負担軽減額含む）を返す。"""
        return (
            self.childbirth_lump_sum
            + self.maternity_allowance
            + self.childcare_leave_benefit
            + self.medical_expense_deduction_relief
        )

    def print_summary(self) -> None:
        """計算結果を表示する。"""
        print("=" * 60)
        print("出産に関する給付金・控除の概算")
        print("=" * 60)
        print(f"出産育児一時金          : {self.childbirth_lump_sum:>12,.0f} 円")
        print(f"出産手当金              : {self.maternity_allowance:>12,.0f} 円")
        print(f"育児休業給付金          : {self.childcare_leave_benefit:>12,.0f} 円")
        print(f"  (対象日数: {self.childcare_leave_days} 日)")
        print(f"医療費控除による軽減額  : {self.medical_expense_deduction_relief:>12,.0f} 円")
        print("-" * 60)
        print(f"合計                    : {self.total():>12,.0f} 円")
        print("=" * 60)
        print("※ 出産手当金は健康保険（会社員等）加入者のみ対象です。")
        print("※ 医療費控除は確定申告が必要です。")
        print("※ 金額はあくまで概算です。詳細は各窓口にご確認ください。")


class BirthAllowanceCalculator:
    """
    出産に関する給付金・控除を計算するクラス。

    Parameters
    ----------
    monthly_salary : float
        月収 (円)。出産手当金・育児休業給付金の算出に使用する。
    childcare_leave_days : int
        育児休業取得日数。デフォルトは 365 日 (1年)。
    medical_expenses : float
        出産にかかった医療費総額 (円)。
    insurance_reimbursement : float
        健康保険等から補填された金額 (円)。
    income_tax_rate : float
        所得税率 (0〜1)。医療費控除の軽減額算出に使用する。デフォルトは 0.10。
    """

    def __init__(
        self,
        monthly_salary: float,
        childcare_leave_days: int = 365,
        medical_expenses: float = 0.0,
        insurance_reimbursement: float = 0.0,
        income_tax_rate: float = 0.10,
    ) -> None:
        if monthly_salary < 0:
            raise ValueError("monthly_salary は 0 以上の値を指定してください。")
        if childcare_leave_days < 0:
            raise ValueError("childcare_leave_days は 0 以上の値を指定してください。")
        if not 0.0 <= income_tax_rate <= 1.0:
            raise ValueError("income_tax_rate は 0〜1 の範囲で指定してください。")
        if medical_expenses < 0:
            raise ValueError("medical_expenses は 0 以上の値を指定してください。")
        if insurance_reimbursement < 0:
            raise ValueError("insurance_reimbursement は 0 以上の値を指定してください。")

        self.monthly_salary = monthly_salary
        self.childcare_leave_days = childcare_leave_days
        self.medical_expenses = medical_expenses
        self.insurance_reimbursement = insurance_reimbursement
        self.income_tax_rate = income_tax_rate

    # ------------------------------------------------------------------
    # 個別計算メソッド
    # ------------------------------------------------------------------

    def calc_childbirth_lump_sum(self) -> int:
        """
        出産育児一時金を返す。

        2023年4月以降は 500,000 円。

        Returns
        -------
        int
            出産育児一時金 (円)
        """
        return CHILDBIRTH_LUMP_SUM

    def calc_maternity_allowance(self) -> float:
        """
        出産手当金の概算を返す。

        計算式:
            標準報酬日額 (= 月収 / 30) × (2/3) × 98日

        健康保険（会社員等）加入者のみ受給できる。

        Returns
        -------
        float
            出産手当金 (円)
        """
        daily_wage = self.monthly_salary / 30.0
        return daily_wage * MATERNITY_ALLOWANCE_RATE * MATERNITY_TOTAL_DAYS

    def calc_childcare_leave_benefit(self) -> float:
        """
        育児休業給付金の概算を返す。

        計算式:
            最初の 180 日: 日額 × 67% × min(取得日数, 180)
            180 日超:      日額 × 50% × max(取得日数 - 180, 0)

        Returns
        -------
        float
            育児休業給付金 (円)
        """
        daily_wage = self.monthly_salary / 30.0
        first_days = min(self.childcare_leave_days, CHILDCARE_LEAVE_THRESHOLD_DAYS)
        remaining_days = max(self.childcare_leave_days - CHILDCARE_LEAVE_THRESHOLD_DAYS, 0)
        return (
            daily_wage * CHILDCARE_LEAVE_RATE_FIRST * first_days
            + daily_wage * CHILDCARE_LEAVE_RATE_AFTER * remaining_days
        )

    def calc_medical_expense_deduction_relief(self) -> float:
        """
        医療費控除による税負担軽減額の概算を返す。

        計算式:
            控除額 = max(医療費 - 保険補填額 - 100,000, 0)
            軽減額 = 控除額 × 所得税率

        Returns
        -------
        float
            税負担軽減額 (円)
        """
        deductible = max(self.medical_expenses - self.insurance_reimbursement - MEDICAL_DEDUCTION_BASE, 0.0)
        return deductible * self.income_tax_rate

    # ------------------------------------------------------------------
    # まとめて計算
    # ------------------------------------------------------------------

    def calculate(self) -> BirthAllowanceSummary:
        """
        すべての給付金・控除を計算して結果を返す。

        Returns
        -------
        BirthAllowanceSummary
            計算結果
        """
        lump_sum = self.calc_childbirth_lump_sum()
        maternity = self.calc_maternity_allowance()
        childcare = self.calc_childcare_leave_benefit()
        medical_relief = self.calc_medical_expense_deduction_relief()

        details = {
            "出産育児一時金": lump_sum,
            "出産手当金": {
                "daily_wage": self.monthly_salary / 30.0,
                "rate": MATERNITY_ALLOWANCE_RATE,
                "days": MATERNITY_TOTAL_DAYS,
                "amount": maternity,
            },
            "育児休業給付金": {
                "daily_wage": self.monthly_salary / 30.0,
                "leave_days": self.childcare_leave_days,
                "first_period_days": min(self.childcare_leave_days, CHILDCARE_LEAVE_THRESHOLD_DAYS),
                "second_period_days": max(self.childcare_leave_days - CHILDCARE_LEAVE_THRESHOLD_DAYS, 0),
                "amount": childcare,
            },
            "医療費控除": {
                "medical_expenses": self.medical_expenses,
                "insurance_reimbursement": self.insurance_reimbursement,
                "deductible_amount": max(
                    self.medical_expenses - self.insurance_reimbursement - MEDICAL_DEDUCTION_BASE, 0.0
                ),
                "income_tax_rate": self.income_tax_rate,
                "relief_amount": medical_relief,
            },
        }

        return BirthAllowanceSummary(
            childbirth_lump_sum=lump_sum,
            maternity_allowance=maternity,
            childcare_leave_benefit=childcare,
            medical_expense_deduction_relief=medical_relief,
            childcare_leave_days=self.childcare_leave_days,
            details=details,
        )
