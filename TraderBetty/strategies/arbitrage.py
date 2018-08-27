"""Provides the the arbitrage strategy components"""
import abc


class ArbitrageStrategyAbstract(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def trade(self):
        """Strategy specific method"""

    @abc.abstractmethod
    def calc_profit(self, *args, **kwargs):
        """Strategy specific method"""


class OnExchangeArbitrageStrategy(ArbitrageStrategyAbstract):
    def trade(self):
        print("I trade sometimes")

    def calc_profit(self, arb_dict, amount=1):
        # Buy amount of base for quote1
        cost = amount * arb_dict.get("prbq1")
        cost += cost * arb_dict.get("buyfee")
        # Get equivalent amount of quote2 if bought for cost
        costq2equiv = cost * arb_dict.get("q1q2")
        costq2equiv -= costq2equiv * arb_dict.get("convfee")
        # Sell amount of base for quote2
        income = amount * arb_dict.get("prbq2")
        income -= income * arb_dict.get("sellfee")
        # Get equivalent amount of quote1 if income sold
        incq1equiv = income * arb_dict.get("q2q1")
        incq1equiv -= incq1equiv * arb_dict.get("convfee")
        spread_q1 = income - costq2equiv
        spread_q2 = incq1equiv - cost
        profit_dict = {
            "cost": cost,
            "costq2": costq2equiv,
            "income": income,
            "inq1": incq1equiv,
            "spread_q1": spread_q1,
            "spread_q2": spread_q2
        }
        return profit_dict
