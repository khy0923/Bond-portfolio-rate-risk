"""
bond_pricing.py
----------------
채권 가격, Macaulay/Modified Duration, Convexity 계산 모듈.
반기이표(semiannual coupon) 미국 국채를 가정한다.
"""
import numpy as np


class Bond:
    def __init__(self, name, face_value, coupon_rate, maturity_years, ytm, freq=2):
        """
        face_value    : 액면가 (예: 100)
        coupon_rate   : 연 쿠폰율 (예: 0.045 = 4.5%)
        maturity_years: 만기(년)
        ytm           : 만기수익률 (연율, 예: 0.045)
        freq          : 연간 이표 지급 횟수 (미국 국채는 2)
        """
        self.name = name
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.maturity_years = maturity_years
        self.ytm = ytm
        self.freq = freq
        self.n_periods = int(round(maturity_years * freq))
        self.coupon_payment = face_value * coupon_rate / freq

    def cashflows(self):
        """(기간번호, 현금흐름) 리스트. 기간 단위는 1/freq 년."""
        cfs = [self.coupon_payment] * self.n_periods
        cfs[-1] += self.face_value
        return cfs

    def price(self, ytm=None):
        """현재가 (할인현금흐름법)."""
        y = self.ytm if ytm is None else ytm
        per_period_rate = y / self.freq
        cfs = self.cashflows()
        pv = sum(cf / (1 + per_period_rate) ** (t + 1) for t, cf in enumerate(cfs))
        return pv

    def macaulay_duration(self, ytm=None):
        y = self.ytm if ytm is None else ytm
        per_period_rate = y / self.freq
        cfs = self.cashflows()
        price = self.price(y)
        weighted_time = sum(
            (t + 1) / self.freq * cf / (1 + per_period_rate) ** (t + 1)
            for t, cf in enumerate(cfs)
        )
        return weighted_time / price

    def modified_duration(self, ytm=None):
        y = self.ytm if ytm is None else ytm
        mac_dur = self.macaulay_duration(y)
        return mac_dur / (1 + y / self.freq)

    def convexity(self, ytm=None):
        y = self.ytm if ytm is None else ytm
        per_period_rate = y / self.freq
        cfs = self.cashflows()
        price = self.price(y)
        conv_sum = sum(
            cf * (t + 1) * (t + 2) / (1 + per_period_rate) ** (t + 3)
            for t, cf in enumerate(cfs)
        )
        # freq^2 로 나눠 '연' 단위 컨벡시티로 변환
        return conv_sum / (price * self.freq ** 2)

    def bpv(self, ytm=None):
        """Basis Point Value: 금리 1bp 변화 시 가격 변화(절대값, per 100 face)."""
        y = self.ytm if ytm is None else ytm
        mod_dur = self.modified_duration(y)
        price = self.price(y)
        return mod_dur * price * 0.0001

    def price_change_duration_only(self, dy):
        """1차 근사(Duration only): dP/P = -ModDur * dy"""
        price = self.price()
        mod_dur = self.modified_duration()
        return -mod_dur * dy * price

    def price_change_duration_convexity(self, dy):
        """2차 근사(Duration + Convexity): dP/P = -ModDur*dy + 0.5*Convexity*dy^2"""
        price = self.price()
        mod_dur = self.modified_duration()
        conv = self.convexity()
        return (-mod_dur * dy + 0.5 * conv * dy ** 2) * price

    def price_exact(self, dy):
        """실제 재평가 가격 변화 (할인율을 dy만큼 이동시켜 재계산)"""
        new_price = self.price(self.ytm + dy)
        return new_price - self.price()

    def __repr__(self):
        return f"Bond({self.name}, {self.maturity_years}Y, coupon={self.coupon_rate:.2%}, ytm={self.ytm:.2%})"
