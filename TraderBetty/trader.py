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
        sq2q1 = "/".join([quote2, quote1])
        # Get the conversion rate for quote1 to quote2
        convfee = 0.0025
        if quote1 == "USD" and quote2 == "EUR":
            q2q1 = self.PM.c.get_rate("EUR", "USD")
            q1q2 = self.PM.c.get_rate("USD", "EUR")
        elif quote1 == "EUR" and quote2 == "USD":
            q2q1 = self.PM.c.get_rate("USD", "EUR")
            q1q2 = self.PM.c.get_rate("EUR", "USD")
        else:
            order = self.PM.get_best_order(exchange, sq2q1)
            q2q1 = order.get("bid", 0)
            q1q2 = 1 / order.get("ask", 0)
            convfee = self.PM.exchanges[exchange].market(sq2q1).get("taker", 0)
        # Get base price in quote1 at which we buy
        sbq1 = "/".join([base, quote1])
        prbq1 = self.PM.get_best_order(exchange, sbq1).get("ask", 0)
        # Get the trading fee for buying
        market = self.PM.exchanges[exchange].market(sbq1) if prbq1 else {}
        buyfee = market.get("taker", 0)
        # Get base price in quote2 at which we sell
        sbq2 = "/".join([base, quote2])
        prbq2 = self.PM.get_best_order(exchange, sbq2).get("bid", 0)
        # Get trading fee for selling
        market = self.PM.exchanges[exchange].market(sbq2) if prbq2 else {}
        sellfee = market.get("taker", 0)
        arb_dict = {
            "base": base,
            "quote1": quote1,
            "quote2": quote2,
            "q2q1": q2q1,
            "q1q2": q1q2,
            "prbq1": prbq1,
            "prbq2": prbq2,
            "buyfee": buyfee,
            "sellfee": sellfee,
            "convfee": convfee
        }
        return arb_dict
