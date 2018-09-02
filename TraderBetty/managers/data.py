"""Provides all data management methods."""
import os
import pandas as pd

from TraderBetty.managers.handlers import DataHandler


class DataManager(DataHandler):
    # TODO: Move all DataFrame conversions to data
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
            extrades.set_index(["exchange", "id"])
        )
        self.extrades[exchange] = extradesdf.copy()
        self.store_csv(extradesdf, extr_path)

        # Update all trades
        tradesdf = pd.concat([self.extrades[ex] for ex in self.exchanges],
                             sort=False)
        self.trades = tradesdf.copy()
        self.store_csv(tradesdf, self.TRADES_PATH)

    def update_ex_price(self, exchange, symbol, price):
        expr_path = "%s/prices_%s.csv" % (self.DATA_PATH,
                                          exchange)
        pricedf = self.exprices[exchange]
        base, quote = symbol.split("/")
        pricedf.loc[base, quote] = price
        self.store_csv(pricedf, expr_path)

    def update_order_book(self, exchange, symbol, order_book):
        ts = order_book.get("timestamp")
        path = "{:s}/orderbook_{:s}_{:s}_{:d}.csv".format(
            self.ORDERBOOK_PATH, exchange, symbol.replace("/", "_"), ts)
        if not os.path.isfile(path):
            self.order_books[exchange][symbol] = pd.DataFrame(
                columns=[("asks", "price"), ("asks", "volume"),
                         ("bids", "price"), ("bids", "volume")])
            self.store_csv(self.order_books[exchange][symbol], path)
        asksdf = pd.DataFrame(order_book.get("asks"),
                              columns=[("asks", "price"), ("asks", "volume")])
        bidsdf = pd.DataFrame(order_book.get("bids"),
                              columns=[("bids", "price"), ("bids", "volume")])
        exobdf = pd.concat([asksdf, bidsdf], axis=1)
        self.order_books[exchange][symbol] = exobdf.copy()
        self.store_csv(exobdf, path)

    def update_ohlcv(self, exchange, symbol, freq, ohlcv):
        path = "{:s}/ohlcv_{:s}_{:s}_{:s}.csv".format(
            self.OHLCV_PATH, exchange, symbol.replace("/", "_"), freq)
        if not os.path.isfile(path):
            self.ohlcvs[exchange][symbol + freq] = pd.DataFrame(
                columns=["datetime", "timestamp", "open", "high", "low",
                         "close", "volume"])
            self.store_csv(self.ohlcvs[exchange][symbol + freq], path)
        ohlcvdf = self.ohlcvs[exchange][symbol + freq].copy()
        if not ohlcvdf.index.name == "datetime":
            ohlcvdf.index = pd.DatetimeIndex(ohlcvdf["datetime"])
        ohlcvdf = ohlcvdf.combine_first(
            ohlcv.set_index("datetime")
        )
        self.ohlcvs[exchange][symbol + freq] = ohlcvdf.copy()
        self.store_csv(ohlcvdf, path)
