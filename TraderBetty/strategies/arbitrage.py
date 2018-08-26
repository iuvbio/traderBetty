"""Provides the the arbitrage strategy components"""
import abc


class ArbitrageStrategyAbstract(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def trade(self):
        pass


class OnExchangeArbitrageStrategy(ArbitrageStrategyAbstract):
    def trade(self):
        pass

    def calc_profit(self, prbq1, conv_prbq2, prbq2, buyfee, sellfee):
        print("Nice profs brah")
