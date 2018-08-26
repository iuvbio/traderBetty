"""The trader class"""


class Trader():
    def __init__(self, portfolio_manager, strategy):
        self.PM = portfolio_manager
        self.exchanges = self.PM.exchanges
        self._trading_strategy = strategy

    def trade(self):
        self._trading_strategy.trade()

    def calc_profit(self):
        self._trading_strategy.calc_profit()

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
        # Get the conversion rate for quote1 to quote2
        if quote1 == "USD" and quote2 == "EUR":
            q2q1 = self.PM.c.get_rate("EUR", "USD")
            q1q2 = self.PM.c.get_rate("USD", "EUR")
        elif quote1 == "EUR" and quote2 == "USD":
            q2q1 = self.PM.c.get_rate("USD", "EUR")
            q1q2 = self.PM.c.get_rate("EUR", "USD")
        else:
            order = self.PM.get_best_order(exchange, "/".join([quote2, quote1]))
            q2q1 = order.get("bid")
            q1q2 = 1 / order.get("ask")
        # Get base price in quote1 at which we buy
        symbol = "/".join([base, quote1])
        prbq1 = self.PM.get_best_order(exchange, symbol).get("ask")
        # Get value of that price in quote2
        conv_prbq2 = prbq1 * q1q2
        # Get the trading fee for buying
        market = self.PM.exchanges[exchange].market(symbol)
        buyfee = market.get("taker")
        # Get base price in quote2 at which we sell
        symbol = "/".join([base, quote2])
        prbq2 = self.PM.get_best_order(exchange, symbol).get("bid")
        # Get value of that price in quote1
        conv_prbq1 = prbq2 * q2q1
        # Get trading fee for selling
        market = self.PM.exchanges[exchange].market(symbol)
        sellfee = market.get("taker")
        # Calculate profit
        spread_q1 = conv_prbq1 - prbq1
        spread_q2 = prbq2 - conv_prbq2
        arb_dict = {
            "prbq1": prbq1,
            "conv_prq2": conv_prbq2,
            "prbq2": prbq2,
            "conv_prbq1": conv_prbq1,
            "spread_q1": spread_q1,
            "spread_q2": spread_q2
        }
        return arb_dict
