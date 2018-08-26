"""The trader class"""


class Trader():
    def __init__(self, portfolio_manager, strategy):
        self.PM = portfolio_manager
        self.exchanges = self.PM.exchanges
        self._trading_strategy = strategy

    def trade(self):
        self._trading_strategy.trade()

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
        prbq1 = self.PM.get_best_order(exchange, "/".join([base, quote1])).get("ask")
        # Get value of that price in quote2
        conv_prbq2 = prbq1 * q1q2
        # Get base price in quote2 at which we sell
        prbq2 = self.PM.get_best_order(exchange, base, quote2).get("bid")
        # Get value of that price in quote1
        conv_prbq1 = prbq2 * q2q1
        # Calculate profit
        spread = conv_prbq1 - prbq1
        return spread
