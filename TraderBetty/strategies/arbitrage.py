"""Provides the the arbitrage strategy components"""
import abc


class ArbitrageStrategyAbstract(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def trade(self):
        pass


class OnExchangeArbitrageStrategy(ArbitrageStrategyAbstract):
    def trade(self):
        pass

    def calc_profit(self, q1q2, q2q1, prbq1, prbq2, buyfee, sellfee, convfee,
                    amount=1):
        # Buy amount of base for quote1
        cost = amount * prbq1
        cost += cost * buyfee
        # Get equivalent amount of quote2 if bought for cost
        costq2equiv = cost * q1q2
        costq2equiv -= costq2equiv * convfee
        # Sell amount of base for quote2
        income = amount * prbq2
        income -= income * sellfee
        # Get equivalent amount of quote1 if income sold
        incq1equiv = income * q2q1
        incq1equiv -= incq1equiv * convfee
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
