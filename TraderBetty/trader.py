"""The trader class"""


class Trader():
    def __init__(self, portfolio_manager, strategy):
        self.PM = portfolio_manager
        self.exchanges = self.PM.exchanges
        self._trading_strategy = strategy

    def trade(self):
        self._trading_strategy.trade()

    def calc_profit(self, arb_dict, amount=1):
        profit = self._trading_strategy.calc_profit(arb_dict, amount)
        return profit

    def limit_buy_order(self, exchange, symbol, amount, price):
        ex = self.exchanges[exchange]
        if symbol in ex.symbols:
            order = ex.create_limit_buy_order(symbol, amount, price)
            order_id = order["id"]
            return order_id
        else:
            print("Symbol not available on {:s}".format(exchange))

    def limit_sell_order(self, exchange, symbol, amount, price):
        ex = self.exchanges[exchange]
        if symbol in ex.symbols:
            order = ex.create_limit_sell_order(symbol, amount, price)
            order_id = order["id"]
            return order_id
        else:
            print("Symbol not available on {:s}".format(exchange))


class ArbitrageTrader(Trader):
    def __init__(self, portfolio_manager, strategy):
        super().__init__(portfolio_manager, strategy)

    def get_data(self, exchange, base, quote1, quote2):
        ex = self.exchanges[exchange]
        sbq1 = "/".join([base, quote1])
        sbq2 = "/".join([base, quote2])
        sq2q1 = "/".join([quote2, quote1])
        sq1q2 = "/".join([quote1, quote2])
        if sbq1 not in ex.symbols or sbq2 not in ex.symbols:
            # Do some logging here
            return None
        if sq2q1 not in ex.symbols and sq1q2 not in ex.symbols:
            # Some more logging
            return None
        # Get fees
        bq1fee = ex.markets[sbq1]["taker"]
        bq2fee = ex.markets[sbq2]["taker"]
        q2q1fee = ex.markets[sq2q1]["taker"] if sq2q1 in ex.symbols else None
        q1q2fee = ex.markets[sq1q2]["taker"] if sq1q2 in ex.symbols else None
        # Get the real prices for q2q1 and q1q2
        if quote1 in ["EUR", "USD"] and quote2 in ["EUR", "USD"]:
            q2q1fee = 0.0025
            q1q2fee = 0.0025
            eurusd = self.PM.c.get_rate("EUR", "USD")
            usdeur = self.PM.c.get_rate("USD", "EUR")
            rq2q1 = usdeur if quote1 == "EUR" else eurusd
            rq1q2 = eurusd if quote1 =="EUR" else usdeur
        else:
            q2q1 = self.PM.get_best_order(
                exchange, sq2q1) if sq2q1 in ex.symbols else None
            q1q2 = self.PM.get_best_order(
                exchange, sq1q2) if sq1q2 in ex.symbols else None
            rq2q1 = 1 / q1q2["ask"] if not q2q1 else q2q1["bid"]
            rq1q2 = 1 / q2q1["ask"] if not q1q2 else q1q2["bid"]
        fees = {
            sbq1: bq1fee,
            sbq2: bq2fee,
            sq2q1: q2q1fee,
            sq1q2: q1q2fee
        }
        # Calculate the implied prices from bq1 and bq2
        bq1 = self.PM.get_best_order(exchange, sbq1)
        bq2 = self.PM.get_best_order(exchange, sbq2)
        iq2q1 = bq1["ask"] / bq2["bid"]
        iq1q2 = bq2["ask"] / bq1["bid"]
        diffq2q1 = rq2q1 - iq2q1
        diffq1q2 = rq1q2 - iq1q2
        diffq2q1rate = diffq2q1 / rq2q1
        diffq1q2rate = diffq1q2 / rq1q2
        arb_dict = {
            sbq1: bq1,
            sbq2: bq2,
            "iq2q1": iq2q1,
            "iq1q2": iq1q2,
            "rq2q1": rq2q1,
            "rq1q2": rq1q2,
            "diffq2q1": diffq2q1,
            "diffq1q2": diffq1q2,
            "diffq2q1rate": diffq2q1rate,
            "diffq1q2rate": diffq1q2rate,
            "fees": fees
        }
        return arb_dict
