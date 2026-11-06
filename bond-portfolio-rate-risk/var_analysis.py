"""
var_analysis.py
----------------
두 가지 VaR 방법론 구현:
1) Delta-Normal (Parametric) VaR: 포트폴리오 Dollar Duration/Convexity와
   과거 금리 변화의 표준편차(정규분포 가정)를 이용
2) Historical Simulation VaR: 실제 일별 금리변화(2Y/5Y/10Y)를
   Duration+Convexity 근사식에 대입해 만든 손익분포의 경험적 분위수 사용
"""
import numpy as np
import pandas as pd
from scipy.stats import norm


def load_yield_changes(csv_path):
    """
    두 가지 CSV 포맷을 자동 인식:
    1) Treasury.gov 원본 포맷: Date(MM/DD/YYYY), 2Yr, 5Yr, 10Yr 등 컬럼명
    2) FRED 병합 포맷: Date(YYYY-MM-DD), 2Y, 5Y, 10Y 컬럼명
    """
    df = pd.read_csv(csv_path)
    cols = set(df.columns)

    if {"2Y", "5Y", "10Y"}.issubset(cols):
        # FRED 포맷
        df["Date"] = pd.to_datetime(df["Date"])
        yields = df[["Date", "2Y", "5Y", "10Y"]].copy()
    else:
        # Treasury.gov 포맷
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        yields = df[["Date", "2Yr", "5Yr", "10Yr"]].copy()
        yields.columns = ["Date", "2Y", "5Y", "10Y"]

    yields = yields.sort_values("Date").reset_index(drop=True)
    # % 단위 -> 소수(연율)로 변환
    for col in ["2Y", "5Y", "10Y"]:
        yields[col] = pd.to_numeric(yields[col], errors="coerce") / 100.0
    yields = yields.dropna().reset_index(drop=True)
    changes = yields[["2Y", "5Y", "10Y"]].diff().dropna().reset_index(drop=True)
    return yields, changes


def delta_normal_var(bonds_dur_dollar, avg_yield_change_std, confidence=0.99, horizon_days=1):
    """
    단일 팩터(평행이동) Delta-Normal VaR.
    bonds_dur_dollar: 포트폴리오 Dollar Duration (= ModDur * MV)
    avg_yield_change_std: 일별 평균 금리변화(팩터)의 표준편차
    """
    z = norm.ppf(confidence)
    sigma_scaled = avg_yield_change_std * np.sqrt(horizon_days)
    var_amount = z * sigma_scaled * bonds_dur_dollar
    return var_amount


def historical_simulation_pnl(bonds, tenor_map, yield_changes_df):
    """
    각 과거 관측일의 실제 (2Y,5Y,10Y) 금리변화를 Duration+Convexity 근사식에
    대입해 포트폴리오 손익 시계열을 생성.
    tenor_map: {"2Y": bond, "5Y": bond, "10Y": bond}
    """
    pnl_list = []
    for _, row in yield_changes_df.iterrows():
        total_pnl = 0.0
        for tenor, bond in tenor_map.items():
            dy = row[tenor]
            total_pnl += bond.price_change_duration_convexity(dy)
        pnl_list.append(total_pnl)
    return pd.Series(pnl_list, name="pnl")


def historical_var(pnl_series, confidence=0.99):
    """손익분포 하위 (1-confidence) 분위수를 VaR(손실금액, 양수)로 반환."""
    alpha = 1 - confidence
    var_amount = -np.percentile(pnl_series, alpha * 100)
    return var_amount


if __name__ == "__main__":
    from portfolio import build_portfolio, portfolio_summary

    bonds = build_portfolio()
    summary = portfolio_summary(bonds)
    D = summary["portfolio_mod_duration"]
    V = summary["total_value"]
    dollar_duration = D * V

    yields, changes = load_yield_changes("data/treasury_yields_fred_2021_2026.csv")
    avg_factor = changes[["2Y", "5Y", "10Y"]].mean(axis=1)
    sigma = avg_factor.std()

    dn_var = delta_normal_var(dollar_duration, sigma, confidence=0.99)
    print(f"[Delta-Normal 99% 1-day VaR] {dn_var:,.0f}")

    pnl = historical_simulation_pnl(bonds, bonds, changes)
    hist_var = historical_var(pnl, confidence=0.99)
    print(f"[Historical Simulation 99% 1-day VaR] {hist_var:,.0f}")
    print(f"관측일수: {len(changes)}일, 손익 표준편차: {pnl.std():,.0f}")
