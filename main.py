#!/usr/bin/env python3
"""
Wrapper for trading on different crypto exchanges using the ccxt library
"""

import ccxt
import time
import json

import pandas as pd
from forex_python.converter import CurrencyRates

IDX = pd.IndexSlice
MYCOINS = ["USD", "EUR", "USDT", "BCH", "DASH", "ETC", "ETH", "LTC", "BTC", "XRP", "IOTA", "GNT", "POWR", "QSP",
           "QTUM", "UBQ", "BTS", "ADA", "GRC", "XVG", "ETN", "MCO", "DOGE", "CANN", "NEO", "OMG", "XLM", "XMR",
           "STEEM", "SKY"]


class Wrapper():
    def __init__(self, api_path, wallets):
        self.c = CurrencyRates()
        self.coins = MYCOINS
        self.DATA_PATH = "data"
        self.API_PATH = api_path

        self.exchanges = {

            "Kraken": {
                "Client": ccxt.kraken(),
                "Currencies": [],
                "Symbols": [],
                "dataKey": "info"
            },

            "Bitfinex": {
                "Client": ccxt.bitfinex(),
                "Currencies": [],
                "Symbols": [],
                "dataKey": "total"
            },

            "Bitstamp": {
                "Client": ccxt.bitstamp(),
                "Currencies": [],
                "Symbols": [],
                "dataKey": None
            },

            "Cryptopia": {
                "Client": ccxt.cryptopia(),
                "Currencies": [],
                "Symbols": [],
                "dataKey": "Data"
            },

            "Binance": {
                "Client": ccxt.binance(),
                "Currencies": [],
                "Symbols": [],
                "dataKey": None
            }

        }

        with open(wallets, "r") as f:
            self.wallets = json.load(f)

        self._initiate_clients()
        self._update_currencies()
        self._update_symbols()

    # method for creating the coindf, should only be run once
    def _make_coindf(self):
        # TODO: asign columns Withdrawal_Fee, Deposit_Fee, Precision, Limit_Max, Limit_Min
        exchanges = [ex for ex in self.exchanges.keys()]
        columns = ["Coin", "Base_Symbols", "Quote_Symbols", "Withdrawal_Fee", "Deposit_Fee", "Precision",
                   "Limit_Max", "Limit_Min", "Balance", "EUR_Balance"]
        index = pd.MultiIndex.from_product([exchanges, columns], names=["Exchanges", "Columns"])
        df = pd.DataFrame(None, index=self.coins, columns=index)
        for exchange in self.exchanges:
            df[exchange]["Balance"] = pd.to_numeric(df[exchange]["Balance"], errors="coerce")

        self.coindf = df

    # methods that get called at initiation, not exchange specific
    def _initiate_clients(self):
        for exchange in self.exchanges:
            with open("%s/%s/ccxt_%s.key" % (self.API_PATH, exchange, exchange.lower())) as f:
                key = f.readline().strip()
                secret = f.readline().strip()
                userid = f.readline().strip()

            self.exchanges[exchange]["Client"].apiKey = key
            self.exchanges[exchange]["Client"].secret = secret

            if exchange == "Bitstamp":
                self.exchanges[exchange]["Client"].uid = userid

            self.exchanges[exchange]["Client"].load_markets()

    def _update_currencies(self):
        for exchange in self.exchanges:
            self.exchanges[exchange]["Currencies"] = self.exchanges[exchange]["Client"].currencies.keys()

    def _update_symbols(self):
        for exchange in self.exchanges:
            self.exchanges[exchange]["Symbols"] = self.exchanges[exchange]["Client"].symbols

    def _match_symbols(self):
        for exchange in self.exchanges:
            client = self.exchanges[exchange]["Client"]
            for coin in self.coindf.index:
                coinbsymbols = []
                coinqsymbols = []
                for symbol in self.exchanges[exchange]["Symbols"]:
                    base = client.market(symbol).get("base")
                    quote = client.market(symbol).get("quote")
                    if base == coin:
                        coinbsymbols.append(client.market(symbol).get("symbol"))
                    if quote == coin:
                        coinqsymbols.append(client.market(symbol).get("symbol"))
                self.coindf[exchange, "Base_Symbols"].loc[coin] = coinbsymbols
                self.coindf[exchange, "Quote_Symbols"].loc[coin] = coinqsymbols

    def _update_balances(self):
        for exchange in self.exchanges:
            balance = self.get_balance(exchange, hide_zero=False)
            for coin in self.coindf.index:
                try:
                    coinbal = balance[coin]
                except KeyError:
                    coinbal = 0
                self.coindf[exchange, "Balance"].loc[coin] = coinbal
                self.coindf[exchange, "EUR_Balance"].loc[coin] = self.convert_to_EUR(exchange, coin, coinbal)
                if exchange == "Bitfinex":
                    time.sleep(2)

    # methods that can be called for individual exchanges
    def convert_to_x(self, exchange, curr1, curr2):
        otherexchanges = [ex for ex in self.exchanges.keys()]
        otherexchanges.remove(exchange)

        symbol = curr1 + "/" + curr2
        exbase_symbols = self.coindf[exchange, "Base_Symbols"].loc[curr1]
        if symbol in exbase_symbols:
            price = self.get_ticker(exchange, symbol)
        else:
            otherprices = self.get_all_ex_lp(otherexchanges, curr1, curr2)
            if otherprices:
                price = max(otherprices)
            else:
                price = None

        return price

    def convert_to_EUR(self, exchange, base, volume):
        """
        Convert an arbitrary amount of a certain currency to Euro.

        1. If the symbol BASE/EUR exists on the original exchange, use that price for the conversion.
        2. Else check if BASE/EUR is available on another exchange, if it is use that price for the conversion.
        3. Else if BASE/EUR is not available on another exchange either, check if BASE/USD is available on the
           original exchange. If it is, use that price to convert to USD, then convert to EUR.
        4. Else check BASE/USDT for original exchange.
        5. Else check BASE/USD for other exchanges.
        6. Else check BASE/USDT for other exchanges.
        3. Else if neither BASE/EUR nor BASE/USD nor BASE/USDT is not available on another exchange either,
           check if BASE/BTC is available on the original exchange. If it is, use that price to convert BASE to BTC.
           3.1 Check if BTC/EUR is available on the original exchange and convert using that price.
           3.2 If it isn't, check if BTC/USD or BTC/USDT are available on original exchange and convert using that
               price.
           3.3 If neither BTC/EUR nor BTC/USD nor BTC/USDT is available on the original exchange
             3.3.1

        :param exchange: The exchange the holding is on
        :param base: The base currency that is to be converted
        :param volume: The amount that should be converted
        :return:
        """

        # TODO: fully implement logic to get EUR price (USDT and exchange's own coin)
        # first look for EUR price on original exchange, then the others
        price = self.convert_to_x(exchange, base, "EUR")

        # second look for USD price on original exchange, then others
        if not price:
            usdrate = self.c.get_rate("USD", "EUR")
            price = self.convert_to_x(exchange, base, "USD")
            if price:
                price = price * usdrate

        if not price:
            btcrate = self.convert_to_x(exchange, "BTC", "EUR")
            price = self.convert_to_x(exchange, base, "BTC")

            if price:
                price = price * btcrate

        if price:
            return volume * price
        else:
            print("%s cannot be exchanged for either EUR, nor USD, nor BTC on any exchange." % base)

    def get_balance(self, exchange, total=True, hide_zero=True, verbose=False):
        client = self.exchanges[exchange]["Client"]

        if total:
            balance = client.fetch_balance()["total"]
            if hide_zero:
                pos_bals = [key for key in balance.keys() if balance[key] > 0]
                balance = {key: value for key, value in balance.items() if key in pos_bals}
        else:
            balance = client.fetch_balance()

        if verbose:
            print(exchange)
            for coin, balance in balance.items():
                print(coin, ": ", balance, "\n")

        return balance

    def get_ticker(self, exchange, symbol, last=True):
        client = self.exchanges[exchange]["Client"]
        if last:
            tick = client.fetch_ticker(symbol)["last"]
        else:
            tick = client.fetch_ticker(symbol)

        return tick

    def get_order_book(self, exchange, symbol):
        client = self.exchanges[exchange]["Client"]
        print(client.fetch_order_book(symbol))

    def get_best_price(self, exchange, symbol):
        client = self.exchanges[exchange]["Client"]
        orderbook = client.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        ask = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None
        print(exchange, 'market price', {'bid': bid, 'ask': ask, 'spread': spread})

    # not exchange specific callable methods
    def get_all_ex_lp(self, exchanges, base, quote):
        symbol = base + "/" + quote
        otherprices = []
        for ex in exchanges:
            client = self.exchanges[ex]["Client"]
            exbase_symbols = self.coindf[ex, "Base_Symbols"].loc[base]
            if symbol in exbase_symbols:
                otherprices.append(self.get_ticker(ex, symbol))

        return otherprices

    def store_coindf(self):
        self.coindf.to_csv("%s/coindf.csv" % self.DATA_PATH, sep=";")
