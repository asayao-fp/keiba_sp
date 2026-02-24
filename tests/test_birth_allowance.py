"""
出産給付金・控除計算モジュールのテスト
"""

import pytest

from src.birth_allowance import (
    BirthAllowanceCalculator,
    BirthAllowanceSummary,
    CHILDBIRTH_LUMP_SUM,
    MATERNITY_TOTAL_DAYS,
    MATERNITY_ALLOWANCE_RATE,
    CHILDCARE_LEAVE_THRESHOLD_DAYS,
    CHILDCARE_LEAVE_RATE_FIRST,
    CHILDCARE_LEAVE_RATE_AFTER,
    MEDICAL_DEDUCTION_BASE,
)


@pytest.fixture
def calculator():
    """基本的な計算機フィクスチャ (月収 30万円)。"""
    return BirthAllowanceCalculator(
        monthly_salary=300_000,
        childcare_leave_days=365,
        medical_expenses=200_000,
        insurance_reimbursement=50_000,
        income_tax_rate=0.10,
    )


class TestBirthAllowanceCalculator:
    def test_childbirth_lump_sum_fixed_amount(self, calculator):
        assert calculator.calc_childbirth_lump_sum() == CHILDBIRTH_LUMP_SUM
        assert calculator.calc_childbirth_lump_sum() == 500_000

    def test_maternity_allowance_formula(self, calculator):
        expected = (300_000 / 30) * MATERNITY_ALLOWANCE_RATE * MATERNITY_TOTAL_DAYS
        assert calculator.calc_maternity_allowance() == pytest.approx(expected)

    def test_maternity_allowance_98_days(self):
        """産前42日 + 産後56日 = 98日が対象日数であることを確認。"""
        assert MATERNITY_TOTAL_DAYS == 98

    def test_childcare_leave_benefit_first_180_days_only(self):
        """育児休業 180 日以内は 67% のみ適用される。"""
        calc = BirthAllowanceCalculator(monthly_salary=300_000, childcare_leave_days=180)
        daily = 300_000 / 30
        expected = daily * CHILDCARE_LEAVE_RATE_FIRST * 180
        assert calc.calc_childcare_leave_benefit() == pytest.approx(expected)

    def test_childcare_leave_benefit_exceeds_180_days(self):
        """育児休業が 180 日を超えた分は 50% 適用。"""
        calc = BirthAllowanceCalculator(monthly_salary=300_000, childcare_leave_days=365)
        daily = 300_000 / 30
        expected = (
            daily * CHILDCARE_LEAVE_RATE_FIRST * 180
            + daily * CHILDCARE_LEAVE_RATE_AFTER * (365 - 180)
        )
        assert calc.calc_childcare_leave_benefit() == pytest.approx(expected)

    def test_childcare_leave_benefit_zero_days(self):
        calc = BirthAllowanceCalculator(monthly_salary=300_000, childcare_leave_days=0)
        assert calc.calc_childcare_leave_benefit() == pytest.approx(0.0)

    def test_medical_expense_deduction_relief(self, calculator):
        # 医療費 200,000 - 補填 50,000 - 基準 100,000 = 50,000 × 10% = 5,000
        expected = (200_000 - 50_000 - MEDICAL_DEDUCTION_BASE) * 0.10
        assert calculator.calc_medical_expense_deduction_relief() == pytest.approx(expected)

    def test_medical_expense_deduction_below_base_is_zero(self):
        """医療費が基準額 (10万円) を超えない場合、控除額は 0。"""
        calc = BirthAllowanceCalculator(
            monthly_salary=300_000,
            medical_expenses=80_000,
            insurance_reimbursement=0,
            income_tax_rate=0.20,
        )
        assert calc.calc_medical_expense_deduction_relief() == pytest.approx(0.0)

    def test_calculate_returns_summary(self, calculator):
        result = calculator.calculate()
        assert isinstance(result, BirthAllowanceSummary)

    def test_summary_total_is_sum_of_components(self, calculator):
        result = calculator.calculate()
        expected_total = (
            result.childbirth_lump_sum
            + result.maternity_allowance
            + result.childcare_leave_benefit
            + result.medical_expense_deduction_relief
        )
        assert result.total() == pytest.approx(expected_total)

    def test_summary_childbirth_lump_sum(self, calculator):
        result = calculator.calculate()
        assert result.childbirth_lump_sum == 500_000

    def test_summary_childcare_leave_days(self, calculator):
        result = calculator.calculate()
        assert result.childcare_leave_days == 365

    def test_summary_details_keys(self, calculator):
        result = calculator.calculate()
        assert "出産育児一時金" in result.details
        assert "出産手当金" in result.details
        assert "育児休業給付金" in result.details
        assert "医療費控除" in result.details

    def test_zero_salary(self):
        """月収 0 円の場合、手当金・給付金も 0 になる。"""
        calc = BirthAllowanceCalculator(monthly_salary=0)
        result = calc.calculate()
        assert result.maternity_allowance == pytest.approx(0.0)
        assert result.childcare_leave_benefit == pytest.approx(0.0)
        assert result.childbirth_lump_sum == 500_000

    def test_invalid_negative_salary_raises(self):
        with pytest.raises(ValueError, match="monthly_salary"):
            BirthAllowanceCalculator(monthly_salary=-1)

    def test_invalid_negative_leave_days_raises(self):
        with pytest.raises(ValueError, match="childcare_leave_days"):
            BirthAllowanceCalculator(monthly_salary=300_000, childcare_leave_days=-1)

    def test_invalid_income_tax_rate_raises(self):
        with pytest.raises(ValueError, match="income_tax_rate"):
            BirthAllowanceCalculator(monthly_salary=300_000, income_tax_rate=1.5)

    def test_invalid_negative_medical_expenses_raises(self):
        with pytest.raises(ValueError, match="medical_expenses"):
            BirthAllowanceCalculator(monthly_salary=300_000, medical_expenses=-1)

    def test_invalid_negative_insurance_reimbursement_raises(self):
        with pytest.raises(ValueError, match="insurance_reimbursement"):
            BirthAllowanceCalculator(monthly_salary=300_000, insurance_reimbursement=-1)

    def test_print_summary_runs_without_error(self, calculator, capsys):
        result = calculator.calculate()
        result.print_summary()
        captured = capsys.readouterr()
        assert "出産育児一時金" in captured.out
        assert "出産手当金" in captured.out
        assert "育児休業給付金" in captured.out
        assert "医療費控除" in captured.out
        assert "合計" in captured.out
