"""
出産・育休・扶養関連の給付金・控除計算テスト
"""

import pytest

from src.benefits.maternity import (
    CHILDBIRTH_LUMP_SUM,
    MATERNITY_LEAVE_DAYS_TOTAL,
    calculate_childbirth_lump_sum,
    calculate_childcare_leave_benefit,
    calculate_dependent_deduction,
    calculate_maternity_benefit,
    calculate_spouse_deduction,
)


class TestChildbirthLumpSum:
    def test_returns_500000(self):
        assert calculate_childbirth_lump_sum() == 500_000

    def test_matches_constant(self):
        assert calculate_childbirth_lump_sum() == CHILDBIRTH_LUMP_SUM


class TestMaternityBenefit:
    def test_standard_calculation(self):
        # 月給30万円: 300000 / 30 * (2/3) * 98 日
        result = calculate_maternity_benefit(300_000)
        expected = 300_000 / 30 * (2 / 3) * MATERNITY_LEAVE_DAYS_TOTAL
        assert abs(result - expected) < 1

    def test_zero_remuneration(self):
        assert calculate_maternity_benefit(0) == 0.0

    def test_custom_days(self):
        result = calculate_maternity_benefit(300_000, days=30)
        expected = 300_000 / 30 * (2 / 3) * 30
        assert abs(result - expected) < 1

    def test_negative_remuneration_raises(self):
        with pytest.raises(ValueError):
            calculate_maternity_benefit(-1)

    def test_negative_days_raises(self):
        with pytest.raises(ValueError):
            calculate_maternity_benefit(300_000, days=-1)

    def test_returns_float(self):
        assert isinstance(calculate_maternity_benefit(300_000), float)


class TestChildcareLeaveBenefit:
    def test_first_180_days_only(self):
        # 月給30万円、180日間
        result = calculate_childcare_leave_benefit(300_000, leave_days=180)
        daily = 300_000 * 12 / 365
        expected_first = daily * 0.67 * 180
        assert abs(result["first_period_amount"] - expected_first) < 1
        assert result["second_period_days"] == 0
        assert result["second_period_amount"] == 0.0

    def test_over_180_days(self):
        result = calculate_childcare_leave_benefit(300_000, leave_days=365)
        assert result["first_period_days"] == 180
        assert result["second_period_days"] == 185
        assert result["total"] == pytest.approx(
            result["first_period_amount"] + result["second_period_amount"]
        )

    def test_total_is_sum_of_periods(self):
        result = calculate_childcare_leave_benefit(400_000, leave_days=300)
        assert result["total"] == pytest.approx(
            result["first_period_amount"] + result["second_period_amount"]
        )

    def test_second_period_lower_than_first(self):
        result = calculate_childcare_leave_benefit(300_000, leave_days=360)
        daily = 300_000 * 12 / 365
        # 同じ日数なら高率期間の方が給付額が多い
        assert result["first_period_amount"] / 180 > result["second_period_amount"] / 180

    def test_zero_wage(self):
        result = calculate_childcare_leave_benefit(0, leave_days=365)
        assert result["total"] == 0.0

    def test_negative_wage_raises(self):
        with pytest.raises(ValueError):
            calculate_childcare_leave_benefit(-1)

    def test_negative_days_raises(self):
        with pytest.raises(ValueError):
            calculate_childcare_leave_benefit(300_000, leave_days=-1)

    def test_returns_dict_with_expected_keys(self):
        result = calculate_childcare_leave_benefit(300_000)
        assert "first_period_days" in result
        assert "second_period_days" in result
        assert "first_period_amount" in result
        assert "second_period_amount" in result
        assert "total" in result


class TestDependentDeduction:
    def test_under_16_no_deduction(self):
        assert calculate_dependent_deduction(0) == 0
        assert calculate_dependent_deduction(15) == 0

    def test_age_16_general(self):
        assert calculate_dependent_deduction(16) == 380_000

    def test_age_18_general(self):
        assert calculate_dependent_deduction(18) == 380_000

    def test_age_19_specified(self):
        assert calculate_dependent_deduction(19) == 630_000

    def test_age_22_specified(self):
        assert calculate_dependent_deduction(22) == 630_000

    def test_age_23_general(self):
        assert calculate_dependent_deduction(23) == 380_000

    def test_age_69_general(self):
        assert calculate_dependent_deduction(69) == 380_000

    def test_age_70_elderly_separate(self):
        assert calculate_dependent_deduction(70) == 480_000

    def test_age_70_elderly_coresident(self):
        assert calculate_dependent_deduction(70, is_coresident_elderly=True) == 580_000

    def test_negative_age_raises(self):
        with pytest.raises(ValueError):
            calculate_dependent_deduction(-1)


class TestSpouseDeduction:
    def test_spouse_income_under_480000_taxpayer_under_9m(self):
        assert calculate_spouse_deduction(5_000_000, 400_000) == 380_000

    def test_spouse_income_exactly_480000(self):
        assert calculate_spouse_deduction(5_000_000, 480_000) == 380_000

    def test_spouse_income_under_480000_taxpayer_9_5m(self):
        assert calculate_spouse_deduction(9_200_000, 400_000) == 260_000

    def test_spouse_income_under_480000_taxpayer_over_9_5m(self):
        assert calculate_spouse_deduction(9_700_000, 400_000) == 130_000

    def test_taxpayer_income_over_10m_no_deduction(self):
        assert calculate_spouse_deduction(10_000_001, 400_000) == 0

    def test_spouse_income_over_1330000_no_deduction(self):
        assert calculate_spouse_deduction(5_000_000, 1_400_000) == 0

    def test_spouse_special_deduction_bracket(self):
        # 配偶者所得 95万円 (480001〜950000), 納税者所得 900万円以下 → 38万円
        assert calculate_spouse_deduction(5_000_000, 900_000) == 380_000

    def test_spouse_special_deduction_higher_bracket(self):
        # 配偶者所得 130万円 (1250001〜1300000), 納税者所得 900万円以下 → 6万円
        assert calculate_spouse_deduction(5_000_000, 1_280_000) == 60_000

    def test_negative_taxpayer_income_raises(self):
        with pytest.raises(ValueError):
            calculate_spouse_deduction(-1, 400_000)

    def test_negative_spouse_income_raises(self):
        with pytest.raises(ValueError):
            calculate_spouse_deduction(5_000_000, -1)
