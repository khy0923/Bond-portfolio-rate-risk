"""
portfolio.py
------------
2026-09-08 미국 국채 par yield curve를 이용해 3개 만기(2Y, 5Y, 10Y)로
구성된 채권 포트폴리오를 만든다. Par bond(발행가=액면가) 가정이므로
coupon_rate = ytm 으로 둔다.
"""
from bond_pricing import Bond

# 2026-09-08 Treasury Par Yield Curve (연율)
LATEST_YIELDS = {
    "2Y": 0.0439,
    "5Y": 0.0457,
    "10Y": 0.0480,
}


def build_portfolio(face_values=None):
    """
    face_values: {"2Y": 금액, "5Y": 금액, "10Y": 금액} (액면가 기준, 단위 자유)
    기본값은 각 3,000,000 (총 9,000,000) 동일가중.
    """
    if face_values is None:
        face_values = {"2Y": 3_000_000, "5Y": 3_000_000, "10Y": 3_000_000}

    bonds = {
        "2Y": Bond("UST 2Y", face_values["2Y"], LATEST_YIELDS["2Y"], 2, LATEST_YIELDS["2Y"]),
        "5Y": Bond("UST 5Y", face_values["5Y"], LATEST_YIELDS["5Y"], 5, LATEST_YIELDS["5Y"]),
        "10Y": Bond("UST 10Y", face_values["10Y"], LATEST_YIELDS["10Y"], 10, LATEST_YIELDS["10Y"]),
    }
    return bonds


def portfolio_summary(bonds):
    """포트폴리오 전체 가치, 가중평균 Duration/Convexity 계산."""
    total_value = 0.0
    weighted_mod_dur = 0.0
    weighted_convexity = 0.0
    rows = []

    # Bond.price()는 face_value 단위 그대로 전체 시장가치를 반환한다
    # (coupon_payment, 원금상환이 모두 face_value 기준으로 계산되므로).
    for key, bond in bonds.items():
        market_value = bond.price()
        total_value += market_value
        rows.append((key, bond, market_value, market_value))

    for key, bond, price_per_100, market_value in rows:
        weight = market_value / total_value
        weighted_mod_dur += weight * bond.modified_duration()
        weighted_convexity += weight * bond.convexity()

    return {
        "total_value": total_value,
        "portfolio_mod_duration": weighted_mod_dur,
        "portfolio_convexity": weighted_convexity,
        "rows": rows,
    }


if __name__ == "__main__":
    bonds = build_portfolio()
    summary = portfolio_summary(bonds)
    print(f"포트폴리오 총 시장가치: {summary['total_value']:,.0f}")
    print(f"포트폴리오 가중평균 Modified Duration: {summary['portfolio_mod_duration']:.4f}")
    print(f"포트폴리오 가중평균 Convexity: {summary['portfolio_convexity']:.4f}")
    for key, bond, price_per_100, market_value in summary["rows"]:
        print(f"  {key}: price={price_per_100:.4f}, MV={market_value:,.0f}, "
              f"ModDur={bond.modified_duration():.4f}, Conv={bond.convexity():.4f}")
