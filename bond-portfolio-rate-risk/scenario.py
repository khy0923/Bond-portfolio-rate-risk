"""
scenario.py
-----------
±10bp, ±50bp, ±100bp, ±200bp 평행이동 시나리오에서
1) 실제 재평가 손익 (Exact)
2) Duration-only 근사 손익
3) Duration+Convexity 근사 손익
을 각 채권 및 포트폴리오 단위로 계산하고, 근사 오차를 비교한다.
"""
import numpy as np
import pandas as pd

SHOCKS_BP = [-200, -100, -50, -10, 10, 50, 100, 200]


def scenario_table(bonds):
    """개별 채권 + 포트폴리오 합산 결과를 DataFrame으로 반환."""
    records = []
    for shock_bp in SHOCKS_BP:
        dy = shock_bp / 10000.0
        exact_total, dur_total, durconv_total = 0.0, 0.0, 0.0
        for key, bond in bonds.items():
            exact = bond.price_exact(dy)
            dur_only = bond.price_change_duration_only(dy)
            dur_conv = bond.price_change_duration_convexity(dy)
            exact_total += exact
            dur_total += dur_only
            durconv_total += dur_conv
        records.append({
            "shock_bp": shock_bp,
            "exact_pnl": exact_total,
            "duration_only_pnl": dur_total,
            "duration_convexity_pnl": durconv_total,
            "duration_only_error": dur_total - exact_total,
            "duration_convexity_error": durconv_total - exact_total,
        })
    return pd.DataFrame(records)


def dense_error_curve(bonds, bp_range=range(-300, 301, 5)):
    """더 촘촘한 금리 변화 범위에서 근사오차 곡선 데이터를 생성 (그래프용)."""
    records = []
    for shock_bp in bp_range:
        dy = shock_bp / 10000.0
        exact_total, dur_total, durconv_total = 0.0, 0.0, 0.0
        for key, bond in bonds.items():
            exact_total += bond.price_exact(dy)
            dur_total += bond.price_change_duration_only(dy)
            durconv_total += bond.price_change_duration_convexity(dy)
        records.append({
            "shock_bp": shock_bp,
            "exact_pnl": exact_total,
            "duration_only_pnl": dur_total,
            "duration_convexity_pnl": durconv_total,
        })
    return pd.DataFrame(records)


if __name__ == "__main__":
    from portfolio import build_portfolio
    bonds = build_portfolio()
    df = scenario_table(bonds)
    pd.set_option("display.float_format", lambda x: f"{x:,.0f}")
    print(df.to_string(index=False))
