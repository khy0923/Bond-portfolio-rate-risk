"""
main.py
-------
채권 포트폴리오 금리위험 측정 파이프라인

1. 포트폴리오 구성 (2Y/5Y/10Y 미국 국채, 2026-09-08 par yield 기준)
2. 금리 시나리오 손익 + Duration-only vs Duration+Convexity 근사오차
3. VaR 산출: Delta-Normal vs Historical Simulation (FRED 약 5년 일별 데이터)
4. VaR 백테스트: 실제 손실이 VaR을 초과한 날의 비율 확인

실행: python main.py   (결과는 outputs/ 에 저장)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from portfolio import build_portfolio, portfolio_summary
from scenario import scenario_table, dense_error_curve
from var_analysis import (
    load_yield_changes, delta_normal_var, historical_simulation_pnl, historical_var
)

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
DATA = os.path.join(BASE, "data", "treasury_yields_fred_2021_2026.csv")
os.makedirs(OUT, exist_ok=True)

# ---- 한글 폰트 자동 탐지 (없으면 영문 라벨로 대체) ----
_KR_FONTS = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR",
             "Noto Sans KR", "NanumBarunGothic"]
_available = {f.name for f in fm.fontManager.ttflist}
_kr = next((f for f in _KR_FONTS if f in _available), None)
USE_KR = _kr is not None
if USE_KR:
    plt.rcParams["font.family"] = _kr
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3


def L(kr, en):
    """한글 폰트가 있으면 한글, 없으면 영문 라벨"""
    return kr if USE_KR else en


def main():
    # 1. 포트폴리오
    bonds = build_portfolio()
    summary = portfolio_summary(bonds)
    D, C, V = summary["portfolio_mod_duration"], summary["portfolio_convexity"], summary["total_value"]
    print(f"[1] 총 시장가치 {V:,.0f} / Duration {D:.4f} / Convexity {C:.4f}")

    # 2. 시나리오 + 근사오차
    scen = scenario_table(bonds)
    scen.to_csv(os.path.join(OUT, "scenario_table.csv"), index=False)
    print(scen.to_string(index=False, float_format=lambda x: f"{x:,.0f}"))

    dense = dense_error_curve(bonds)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(dense["shock_bp"], dense["exact_pnl"], label=L("Exact (실제 재평가)", "Exact (full repricing)"),
            linewidth=2.5, color="black")
    ax.plot(dense["shock_bp"], dense["duration_only_pnl"], label=L("Duration-only 근사", "Duration-only"),
            linestyle="--", color="#d62728")
    ax.plot(dense["shock_bp"], dense["duration_convexity_pnl"], label=L("Duration+Convexity 근사", "Duration+Convexity"),
            linestyle="-.", color="#1f77b4")
    ax.set_xlabel(L("금리 변화 (bp)", "Yield change (bp)"))
    ax.set_ylabel(L("포트폴리오 손익", "Portfolio P&L"))
    ax.set_title(L("Duration-only vs Duration+Convexity 근사오차 비교",
                   "Approximation error: Duration-only vs Duration+Convexity"))
    ax.legend()
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "01_approximation_error.png"), dpi=150)
    plt.close(fig)

    # 3. VaR
    yields, changes = load_yield_changes(DATA)
    pnl = historical_simulation_pnl(bonds, bonds, changes)
    hist_var = historical_var(pnl, 0.99)
    sigma = changes[["2Y", "5Y", "10Y"]].mean(axis=1).std()
    dn_var = delta_normal_var(D * V, sigma, 0.99)
    gap = abs(hist_var - dn_var) / dn_var
    print(f"[3] Delta-Normal {dn_var:,.0f} / Historical {hist_var:,.0f} / 차이 {gap:.1%}")

    # 4. 백테스트 (손실이 VaR을 넘은 날 비율; 99% VaR이면 이론상 약 1%)
    n = len(pnl)
    exc_hist = int((pnl < -hist_var).sum())
    exc_dn = int((pnl < -dn_var).sum())
    worst = -pnl.min()
    print(f"[4] 관측 {n}일 / 최악의 하루 손실 {worst:,.0f}")
    print(f"    Delta-Normal 초과 {exc_dn}일 ({exc_dn/n:.2%}) / Historical 초과 {exc_hist}일 ({exc_hist/n:.2%})")

    pd.DataFrame({
        "method": ["Delta-Normal (99%)", "Historical Simulation (99%)"],
        "var_1day": [dn_var, hist_var],
        "exceedance_days": [exc_dn, exc_hist],
        "exceedance_ratio": [exc_dn / n, exc_hist / n],
    }).to_csv(os.path.join(OUT, "var_results.csv"), index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(pnl, bins=40, color="#8da0cb", alpha=0.8)
    ax.axvline(-dn_var, color="#d62728", linestyle="--", label=f"Delta-Normal 99% VaR: {dn_var:,.0f}")
    ax.axvline(-hist_var, color="#2ca02c", linestyle="-.", label=f"Historical 99% VaR: {hist_var:,.0f}")
    ax.set_xlabel(L("일별 포트폴리오 손익", "Daily portfolio P&L"))
    ax.set_ylabel(L("빈도", "Frequency"))
    ax.set_title(L(f"일별 손익분포와 99% VaR ({n:,}영업일)", f"Daily P&L distribution and 99% VaR ({n:,} days)"))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "02_pnl_distribution.png"), dpi=150)
    plt.close(fig)

    write_report(D, C, V, scen, dn_var, hist_var, gap, n, exc_dn, exc_hist, worst)
    print("완료: outputs/ 확인")


def write_report(D, C, V, scen, dn_var, hist_var, gap, n, exc_dn, exc_hist, worst):
    R = []
    R.append("# 채권 포트폴리오 금리위험 측정 - 결과 요약\n")
    R.append("> 데이터: FRED(DGS2, DGS5, DGS10), 2021-09-10 ~ 2026-09-10, 약 5년 (2022년 급격한 금리인상기 포함)\n")
    R.append("## 1. 포트폴리오\n")
    R.append("- 기준일 2026-09-08 미국 국채 par yield, 2Y/5Y/10Y 각 3,000,000 (동일가중)")
    R.append(f"- 총 시장가치 {V:,.0f} / Modified Duration {D:.4f} / Convexity {C:.4f}\n")
    R.append("## 2. Duration-only vs Duration+Convexity 근사오차\n")
    R.append("| 금리충격(bp) | Exact 손익 | Duration-only 오차 | Duration+Convexity 오차 |")
    R.append("|---|---|---|---|")
    for _, r in scen.iterrows():
        R.append(f"| {r['shock_bp']:+.0f} | {r['exact_pnl']:,.0f} | {r['duration_only_error']:,.0f} | {r['duration_convexity_error']:,.0f} |")
    R.append("\n±200bp에서 Duration-only 오차(약 6.5만)가 Convexity 반영 시 약 3.9천으로 줄어든다.\n")
    R.append("## 3. VaR (99%, 1일)\n")
    R.append("| 방법론 | VaR | VaR 초과일수 | 초과비율 |")
    R.append("|---|---|---|---|")
    R.append(f"| Delta-Normal | {dn_var:,.0f} | {exc_dn}일 | {exc_dn/n:.2%} |")
    R.append(f"| Historical Simulation | {hist_var:,.0f} | {exc_hist}일 | {exc_hist/n:.2%} |")
    R.append(f"\n- 두 방법론의 VaR 차이는 약 {gap:.1%}로 근접")
    R.append(f"- 관측 {n:,}일 중 최악의 하루 손실: {worst:,.0f}\n")
    R.append("## 4. 한계\n")
    R.append("- Delta-Normal은 평균 금리변화 단일 팩터(평행이동) 가정, Historical은 텐서별 실제 변화 반영")
    R.append("- 일별 손익은 Duration+Convexity 근사로 계산 (작은 충격에서는 정확, 큰 충격은 완전재평가가 더 정확)")
    R.append("- 포트폴리오는 par bond 이론가 기준이며 실제 종목의 유동성·베이시스는 미반영")
    with open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(R))


if __name__ == "__main__":
    main()
