#!/usr/bin/env python3
"""
Wrapper for trading on different crypto exchanges using the ccxt library
"""

import ccxt
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
        self._update_balances()
        self._update_eur_balance()

    # method for creating the coindf, should only be run once
    def _make_coindf(self):
        # TODO: asign columns Withdrawal_Fee, Deposit_Fee, Precision, Limit_Max, Limit_Min
        exchanges = [ex for ex in self.exchanges.keys()]
        columns = ["Base_Symbols", "Quote_Symbols", "Withdrawal_Fee", "Deposit_Fee", "Precision",
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
                    market = client.market(symbol)
                    base = market.get("base")
                    quote = market.get("quote")
                    if base == coin:
                        coinbsymbols.append(market.get("symbol"))
                    if quote == coin:
                        coinqsymbols.append(market.get("symbol"))
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

        total_balances = []
        for coin in self.coindf.index:
            total_balances.append(self.coindf.loc[coin][:, "Balance"].sum())
        self.coindf["Total_Balance"] = total_balances

    def _update_eur_balance(self):
        usdrate = self.c.get_rate("USD", "EUR")
        btceurprices = self.get_all_ex_lp("BTC", "EUR")
        btcrate = btceurprices[0][1]
        for coin in self.coindf.index:
            if self.coindf["Total_Balance"].loc[coin] > 0:
                eurprices = self.get_all_ex_lp(coin, "EUR")
                if eurprices:
                    bestprice = eurprices[0][1]
                    usdprices = None
                    btcprices = None
                else:
                    usdprices = self.get_all_ex_lp(coin, "USD")
                    if usdprices:
                        bestprice = usdprices[0][1] * usdrate
                        btcprices = None
                    else:
                        btcprices = self.get_all_ex_lp(coin, "BTC")
                        if btcprices:
                            bestprice = btcprices[0][1] * btcrate
                        else:
                            bestprice = 0

                for exchange in self.exchanges:
                    coinbal = self.coindf[exchange, "Balance"].loc[coin]
                    if coinbal > 0:
                        price = bestprice
                        if eurprices:
                            eurprices = dict(eurprices)
                            if exchange in eurprices.keys():
                                price = eurprices[exchange]
                        elif usdprices:
                            usdprices = dict(usdprices)
                            if exchange in usdprices.keys():
                                price = usdprices[exchange] * usdrate
                        elif btcprices:
                            btcprices = dict(btcprices)
                            if exchange in btcprices.keys():
                                price = btcprices[exchange] * btcrate
                        else:
                            pass

                        convbal = coinbal * price

                    else:
                        convbal = 0

                    self.coindf[exchange, "EUR_Balance"].loc[coin] = convbal

        total_balances = []
        for coin in self.coindf.index:
            total_balances.append(self.coindf.loc[coin][:, "EUR_Balance"].sum())
        self.coindf["Total_EUR_Balance"] = total_balances

    # methods that can be called for individual exchanges
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

    def get_best_order(self, exchange, symbol, verbose=False):
        client = self.exchanges[exchange]["Client"]
        orderbook = client.fetch_order_book(symbol)
        bid = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        ask = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None

        if verbose:
            print(exchange, 'market price', {'bid': bid, 'ask': ask, 'spread': "%.2f%%" % spread})

        return {"bid": bid, "ask": ask}

    def get_fee(self, exchange, coin, quote="BTC"):
        symbol = coin + "/" + quote
        client = self.exchanges[exchange]["Client"]
        try:
            market = client.market(symbol)
            fee = market.get("taker")
        except ccxt.ExchangeError:
            print("Symbol not available on %s" % exchange)
            fee = None

        return fee

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

        prices = sorted(prices.items(), key=lambda x: x[1], reverse=True)

        return prices

    def get_best_price(self, base, quote, exchanges=None):
        prices = self.get_all_ex_lp(base, quote, exchanges=exchanges)
        bestex = prices[0][0]
        bestprice = prices[0][1]

        return (bestex, bestprice)

    def get_all_ex_bid_ask(self, base, quote, exchanges=None):
        symbol = base + "/" + quote
        if not exchanges:
            exchanges = self.exchanges.keys()

        orders = {}
        for ex in exchanges:
            exbase_symbols = self.coindf[ex, "Base_Symbols"].loc[base]
            # exquote_symbols = self.coindf[ex, "Base_Symbols"].loc[base]
            if symbol in exbase_symbols:
                orders[ex] = self.get_best_order(ex, symbol)

        return orders

    def get_best_ask(self, base, quote, exchanges=None):
        orders = self.get_all_ex_bid_ask(base, quote, exchanges=exchanges)
        orders = sorted(orders.items(), key=lambda x: x[1]["ask"])
        bestex = orders[0][0]
        bestask = orders[0][1]["ask"]

        return (bestex, bestask)

    def get_best_bid(self, base, quote, exchanges=None):
        orders = self.get_all_ex_bid_ask(base, quote, exchanges=exchanges)
        orders = sorted(orders.items(), key=lambda x: x[1]["bid"], reverse=True)
        bestex = orders[0][0]
        bestbid = orders[0][1]["bid"]

        return (bestex, bestbid)

    def convert_to_eur(self, base, volume=1):
        # TODO: fully implement logic to get EUR price (USDT and exchange's own coin)
        eurprices = self.get_all_ex_lp(base, "EUR")
        if eurprices:
            ex = eurprices[0][0]
            price = eurprices[0][1]
            curr = "EUR"
        else:
            usdprices = self.get_all_ex_lp(base, "USD")
            if usdprices:
                usdrate = self.c.get_rate("USD", "EUR")
                ex = usdprices[0][0]
                price = usdprices[0][1]
                price *= usdrate
                curr = "USD"
            else:
                btcprices = self.get_all_ex_lp(base, "BTC")
                btceurprices = self.get_all_ex_lp("BTC", "EUR")
                btcrate = btceurprices[0][1]
                if btcprices:
                    ex = btcprices[0][0]
                    price = btcprices[0][1]
                    price *= btcrate
                    curr = "BTC"
                else:
                    ex = None
                    price = None
                    curr = None

        if price:
            amt = volume * price
        else:
            print("%s cannot be exchanged for either EUR, nor USD, nor BTC on any exchange." % base)
            amt = 0

        return {"Exchange": ex, "Amount": amt, "Currency": curr}

    def store_coindf(self):
        self.coindf.to_csv("%s/coindf.csv" % self.DATA_PATH, sep=";")

    def calc_spread(self, price1, price2):
        prices = [price1, price2]
        max_p = max(prices)
        min_p = min(prices)
        spread = max_p - min_p
        spread_rate = spread / min_p

        return {"buy_price": min_p, "sell_price": max_p, "spread": spread, "spread_p": spread_rate}

    def calc_profit(self, price1, price2, volume=1, buy_curr="EUR", sell_curr="USD"):
        # Buy x BTC at price1 and apply trading fee
        cost = volume * price1
        cost += cost * fee
        # Sell x BTC at price 2 and apply trading fee
        income = volume * price2
        income -= income * fee
        # Convert to base currency and apply conversion surcharge
        rincome = income * self.c.get_rate(sell_curr, buy_curr)
        profit = rincome - cost

        return profit

    def get_portfolio_value(self, quote="EUR"):
        if quote == "EUR":
            total = self.coindf["Total_EUR_Balance"].sum()
            return total
