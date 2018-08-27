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
        if not arb_dict:
            return None
        # Buy amount of base for quote1
        cost = amount * arb_dict.get("prbq1")
        # Get equivalent amount of quote2 if bought for cost
        costq2equiv = cost * arb_dict.get("q1q2")
        # Sell amount of base for quote2
        income = amount * arb_dict.get("prbq2")
        # Get equivalent amount of quote1 if income sold
        incq1equiv = income * arb_dict.get("q2q1")
        # Apply trading fees
        cost += cost * arb_dict.get("buyfee")
        costq2equiv += costq2equiv * arb_dict.get("convfee")
        income -= income * arb_dict.get("sellfee")
        incq1equiv -= incq1equiv * arb_dict.get("convfee")
        # Calculate the profit
        profitq1 = income - costq2equiv
        profitq2 = incq1equiv - cost
        profit_dict = {
            "base": arb_dict.get("base"),
            "buyin": arb_dict.get("quote1"),
            "sellin": arb_dict.get("quote2"),
            "cost": cost,
            "costq2": costq2equiv,
            "inc": income,
            "incq1": incq1equiv,
            "profitq1": profitq1,
            "profitq2": profitq2
        }
        return profit_dict
