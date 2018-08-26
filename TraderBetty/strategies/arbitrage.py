"""Provides the the arbitrage strategy components"""
import abc


class ArbitrageStrategyAbstract(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def trade(self):
        pass


class OnExchangeArbitrageStrategy(ArbitrageStrategyAbstract):
    def trade(self):
        pass
