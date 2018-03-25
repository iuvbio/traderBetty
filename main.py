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


class Trader():
    def __init__(self, api_path, wallets):
        """
        The API path should be a directory containing a directory for each exchange which contains a key file
        named after the exchange as well.
        Wallets is a json file containing containing a dictionary with the wallet names as keys for another dictionary
        with the currencies as keys and the corresponding balance as value.
        :param api_path:
        :param wallets:
        """
        self.c = CurrencyRates()
        self.coins = MYCOINS
        self.DATA_PATH = "data"
        self.API_PATH = api_path

        self.exchanges = {

            "Kraken": {
                "Client": ccxt.kraken(),
                "Currencies": [],
                "Symbols": []
            },

            "Bitfinex": {
                "Client": ccxt.bitfinex(),
                "Currencies": [],
                "Symbols": []
            },

            "Bitstamp": {
                "Client": ccxt.bitstamp(),
                "Currencies": [],
                "Symbols": []
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
                "Symbols": []
            }

        }

        self.last_prices = {}

        with open(wallets, "r") as f:
            self.wallets = json.load(f)

        self._initiate_clients()
        self._update_currencies()
        self._update_symbols()
        self._make_coindf()
        self._match_symbols()

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
        # TODO: Solve the err_rate_limit error on Bitfinex
        for exchange in self.exchanges:
            balance = self.get_balance(exchange, hide_zero=False)
            for coin in self.coindf.index:
                try:
                    coinbal = balance[coin]
                except KeyError:
                    coinbal = 0
                self.coindf[exchange, "Balance"].loc[coin] = coinbal

    def update_EUR_balance(self):
        usdrate = self.c.get_rate("USD", "EUR")
        btceurprices = self.get_all_ex_lp("BTC", "EUR")
        btcrate = list(self.get_best_price(btceurprices).values())[0]
        for coin in self.coindf.index:
            eurprices = self.get_all_ex_lp(coin, "EUR")
            usdprices = self.get_all_ex_lp(coin, "USD")
            btcprices = self.get_all_ex_lp(coin, "BTC")
            bestprice = self.convert_to_EUR(coin)
            for exchange in self.exchanges:
                if exchange in eurprices.keys():
                    price = eurprices[exchange]
                elif exchange in usdprices.keys():
                    price = usdprices[exchange] * usdrate
                elif exchange in btcprices.keys():
                    price = btcprices[exchange] * btcrate
                else:
                    price = bestprice

                if price:
                    coinbal = self.coindf[exchange, "Balance"].loc[coin] * price
                else:
                    coinbal = 0

                self.coindf[exchange, "EUR_Balance"].loc[coin] = coinbal

        # if exchange == "Bitfinex":
        #     time.sleep(2)

    # methods that can be called for individual exchanges
    def convert_to_EUR(self, base, volume=1, exchange=None):
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
        eurprices = self.get_all_ex_lp(base, "EUR")
        if exchange:
            if eurprices and exchange in eurprices.keys():
                price = eurprices[exchange]
            else:
                usdprices = self.get_all_ex_lp(base, "USD")
                if usdprices and exchange in usdprices.keys():
                    usdrate = self.c.get_rate("USD", "EUR")
                    price = usdprices[exchange]
                    price *= usdrate
                else:
                    btcprices = self.get_all_ex_lp(base, "BTC")
                    btceurprices = self.get_all_ex_lp("BTC", "EUR")
                    btcrate = list(self.get_best_price(btceurprices).values())[0]
                    if btcprices and exchange in btcprices:
                        price = btcprices[exchange]
                        price *= btcrate
                    else:
                        price = None

        else:
            if eurprices:
                price = list(self.get_best_price(eurprices).values())[0]
            else:
                usdprices = self.get_all_ex_lp(base, "USD")
                # second look for USD price on original exchange, then others
                if usdprices:
                    usdrate = self.c.get_rate("USD", "EUR")
                    price = list(self.get_best_price(usdprices).values())[0]
                    price *= usdrate
                else:
                    btcprices = self.get_all_ex_lp(base, "BTC")
                    btceurprices = self.get_all_ex_lp("BTC", "EUR")
                    btcrate = list(self.get_best_price(btceurprices).values())[0]
                    if btcprices:
                        price = list(self.get_best_price(btcprices).values())[0]
                        price *= btcrate
                    else:
                        price = None
        if price:
            return volume * price
        else:
            if exchange:
                print("No conversion is possible on %s" % exchange)
            else:
                print("%s cannot be exchanged for either EUR, nor USD, nor BTC on any exchange." % base)
            return price

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

    def get_best_order(self, exchange, symbol):
        client = self.exchanges[exchange]["Client"]
        orderbook = client.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        ask = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None
        print(exchange, 'market price', {'bid': bid, 'ask': ask, 'spread': spread})

    # not exchange specific callable methods
    def get_all_ex_lp(self, base, quote, exchanges=None):
        symbol = base + "/" + quote
        prices = {}
        if not exchanges:
            exchanges = self.exchanges.keys()

        for ex in exchanges:
            exbase_symbols = self.coindf[ex, "Base_Symbols"].loc[base]
            if symbol in exbase_symbols:
                lp = self.get_ticker(ex, symbol)
                prices[ex] = lp

        return prices

    def get_best_price(self, prices):
        best_ex = max(prices, key=lambda key: prices[key])
        bestprice = {best_ex: prices[best_ex]}

        return bestprice

    def store_coindf(self):
        self.coindf.to_csv("%s/coindf.csv" % self.DATA_PATH, sep=";")

    def calc_spread(self, price, price_b=None):
        if price_b:
            prices = [price, price_b]
        else:
            prices = price
        max_p = max(prices)
        min_p = min(prices)
        spread = max_p - min_p
        spread_p = spread / min_p

        return {"buy_price": min_p, "sell_price": max_p, "spread": spread, "spread_p": spread_p}

    def calc_profit(self, exchange, price1, price2, fee, volume=1, buy_curr="EUR", sell_curr="USD"):
        # Buy x BTC at price1 and apply trading fee
        cost = volume * price1
        cost += cost * fee
        # Sell x BTC at price 2 and apply trading fee
        income = volume * price2
        income -= income * fee
        # Convert to base currency and apply conversion surcharge
        rincome = income * self.convert_to_x(exchange, sell_curr, buy_curr)
        profit = rincome - cost

        return profit
