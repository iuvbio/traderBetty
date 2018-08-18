"""Provides all data management methods."""
import pandas as pd

from TraderBetty.managers.handlers import DataHandler


class DataManager(DataHandler):
    def update_balance(self, column, balance):
        balance = pd.Series(balance, name=column)
        self.balances[column] = balance
        self.balances.fillna(0, inplace=True)
        self.balances["total"] = self.balances[
            [c for c in list(self.balances.columns) if
             c in list(self.exchanges) + list(self.wallets)]
        ].sum(axis=1)
        self.store_csv(
            self.balances, self.BALANCE_PATH)

    def update_trades(self, exchange, extrades):
        # Update exchange specific trades
        extr_path = "%s/trades_%s.csv" % (self.DATA_PATH,
                                          exchange)
        extradesdf = self.extrades[exchange].copy()
        if not extradesdf.index.names == ["exchange", "id"]:
            extradesdf.set_index(["exchange", "id"], inplace=True)
        extradesdf = extradesdf.combine_first(
            extrades.set_index(["exchange", "id"])  # drop=False
        )
        self.extrades[exchange] = extradesdf.copy()
        self.store_csv(extradesdf, extr_path)

        # Update all trades
        tradesdf = self.trades.copy()
        if not tradesdf.index.names == ["exchange", "id"]:
            tradesdf.set_index(["exchange", "id"], inplace=True)
        tradesdf = tradesdf.combine_first(
            extrades.set_index(["exchange", "id"])  # drop=False
        )
        self.trades = tradesdf.copy()
        self.store_csv(tradesdf, self.TRADES_PATH)

    def update_ex_price(self, exchange, symbol, price):
        expr_path = "%s/prices_%s.csv" % (self.DATA_PATH,
                                          exchange)
        pricedf = self.exprices[exchange]
        base, quote = symbol.split("/")
        pricedf.loc[base, quote] = price
        self.store_csv(pricedf, expr_path)
