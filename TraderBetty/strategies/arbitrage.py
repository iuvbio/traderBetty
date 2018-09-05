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

    def calc_profit(self, arb_dict, amount=None, q1=None, q2=None):
        if not arb_dict:
            return None
        if amount and (q1 or q1):
            # Some logging here
            print("Specify either an amount to buy or a cost in either quote currency.")
            return None
        if q1:
            # TODO: Add correct key to dict here
            cost = q1
            buycurr = arb_dict["quote1"]
            sellcurr = arb_dict["quote2"]
        elif q2:
            cost = q2
            buycurr = arb_dict["quote2"]
            sellcurr = arb_dict["quote1"]
        else:
            cost = None
            amount = amount if amount else 1
            buycurr = arb_dict["quote1"] if arb_dict["diffq2q1"] > 0 else (
                    arb_dict["quote2"]
            )
            sellcurr = arb_dict["quote2"] if buycurr != arb_dict["quote2"] else arb_dict["quote1"]
        buy = "{:s}/{:s}".format(arb_dict["base"], buycurr)
        sell = "{:s}/{:s}".format(arb_dict["base"], sellcurr)
        conv = "{:s}/{:s}".format(sellcurr, buycurr)
        # Buy amount of base for quote1
        amount = cost / arb_dict[buy]["ask"] if not amount else amount
        cost = amount * arb_dict[buy]["ask"]
        # Sell amount of base for quote2
        income = amount * arb_dict[sell]["bid"]
        # Apply trading fees
        cost += cost * arb_dict["fees"][buy]
        income -= income * arb_dict["fees"][sell]
        income_conv = income * arb_dict["rq2q1"]  if (
                buycurr == arb_dict["quote1"]) else (
            income * arb_dict["rq1q2"]
        )
        convfee = arb_dict["fees"][conv] if arb_dict["fees"][conv] else (
            arb_dict["fees"]["{:s}/{:s}".format(buycurr, sellcurr)]
        )
        income_conv -= income_conv * convfee
        # Calculate the profit
        profit = income_conv - cost
        profit_dict = {
            "buy": buy,
            "sell": sell,
            "amount": amount,
            "cost": cost,
            "inc": income_conv,
            "profit": profit,
        }
        return profit_dict

    def is_profitable(self, profit_dict):
        if profit_dict.get("profit") > 0:
            return True
