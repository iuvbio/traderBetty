#!/usr/bin/env python3

import os
import time
import json
import ccxt
from itertools import combinations

import pandas as pd
from configparser import ConfigParser
from forex_python.converter import CurrencyRates


class PortfolioManager():
    def __init__(self, config_path, api_path, wallets=None):
        """

        :param config_path:
        :param api_path:
        :param wallets:
        """
        config = ConfigParser()
        config.read(config_path)
        self.coins = config.get("main", "coins").split(",")
        self.exchanges = {ex: {} for ex in config.get("main", "exchanges").split(",")}
        self.c = CurrencyRates()
        self.DATA_PATH = "data"
        self.API_PATH = api_path

        # check if the path is to a valid file
        if not os.path.isfile(config_path) or not os.path.isfile(api_path):
            raise ValueError
        # load the api keys from config
        with open(api_path) as file:
            keys = json.load(file)

        for id in keys:
            exchange = getattr(ccxt, id)
            exchange_config = {}
            exchange_config.update(keys[id])
            self.exchanges[id]["Client"] = exchange(exchange_config)

        self.last_prices = {}

        #TODO: implement wallet address tracking
        if wallets:
            with open(wallets, "r") as f:
                self.wallets = json.load(f)

        self._initiate_markets()
        self._update_currencies()
        self._update_symbols()

        if os.path.isfile("%s/coindf.csv" % self.DATA_PATH):
            first_run = False

        self._make_coindf()
        self._match_symbols()

        self._update_balances()
        self._update_eur_balance()
        self._update_fees()

    # method for creating the coindf, should only be run once
    def _make_coindf(self):
        # TODO: asign columns Precision, Limit_Max, Limit_Min
        exchanges = [ex for ex in self.exchanges.keys()]
        columns = ["Base_Symbols", "Quote_Symbols", "Withdrawal_Fee", "Deposit_Fee", "Precision",
                   "Limit_Max", "Limit_Min", "Balance", "EUR_Balance"]
        index = pd.MultiIndex.from_product([exchanges, columns], names=["Exchanges", "Columns"])
        df = pd.DataFrame(None, index=self.coins, columns=index)

        self.coindf = df

    # methods that get called at initiation, not exchange specific
    def _initiate_markets(self):
        for exchange in self.exchanges:
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
        for exchange in self.exchanges:
            balance = self.get_balance(exchange, hide_zero=False)
            for coin in self.coindf.index:
                try:
                    coinbal = balance[coin]
                except KeyError:
                    coinbal = 0
                self.coindf.loc[coin, (exchange, "Balance")] = coinbal

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
                    coinbal = self.coindf.loc[coin, (exchange, "Balance")]
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

                    self.coindf.loc[coin, (exchange, "EUR_Balance")] = convbal

        total_balances = []
        for coin in self.coindf.index:
            total_balances.append(self.coindf.loc[coin][:, "EUR_Balance"].sum())
        self.coindf["Total_EUR_Balance"] = total_balances

    def _update_fees(self):
        for exchange in self.exchanges.keys():
            for coin in self.coins:
                deposit, withdrawal = self.get_funding_fee(exchange, coin)
                self.coindf[exchange, "Withdrawal_Fee"].loc[coin] = withdrawal
                self.coindf[exchange, "Deposit_Fee"].loc[coin] = deposit

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
        if client.has["fetchTicker"]:
            delay = int(client.rateLimit / 1000)
            time.sleep(delay)
            if last:
                tick = client.fetch_ticker(symbol)["last"]
            else:
                tick = client.fetch_ticker(symbol)

            return tick
        else:
            print("%s doesn't support fetch_ticker()" % exchange)

    def get_order_book(self, exchange, symbol):
        client = self.exchanges[exchange]["Client"]
        if client.has["fetchOrderBook"]:
            delay = int(client.rateLimit / 1000)
            time.sleep(delay)
            return client.fetch_order_book(symbol)
        else:
            print("%s doesn't support fetch_order_book()")

    def get_best_order(self, exchange, symbol, verbose=False):
        orderbook = self.get_order_book(exchange, symbol)
        bid = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        ask = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None

        if verbose:
            print(exchange, 'market price', {'bid': bid, 'ask': ask, 'spread': "%.2f%%" % spread})

        return {"bid": bid, "ask": ask}

    def get_ohlcv(self, exchange, symbol, timeframe="1d"):
        client = self.exchanges[exchange]["Client"]
        if client.has["fetchOHLCV"]:
            delay = int(client.rateLimit / 1000)
            time.sleep(delay)
            ohlcv = client.fetch_ohlcv(symbol, timeframe)
            return ohlcv
        else:
            print("%s doesn't support fetch_ohlcv()" % exchange)

    def get_trading_fee(self, exchange, coin, quote="BTC"):
        symbol = coin + "/" + quote
        client = self.exchanges[exchange]["Client"]
        try:
            market = client.market(symbol)
            fee = market.get("taker")
        except ccxt.ExchangeError:
            print("Symbol not available on %s" % exchange)
            fee = None

        return fee

    def get_funding_fee(self, exchange, coin):
        client = self.exchanges[exchange]["Client"]
        fees = client.fees["funding"]
        try:
            deposit = fees["deposit"][coin]
            withdrawal = fees["withdraw"][coin]
        except KeyError:
            # print("%s not available on %s" % (coin, exchange))
            deposit = None
            withdrawal = None

        return deposit, withdrawal

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

    def load_coindf(self):
        df = pd.read_csv("%s/coindf.csv" % self.DATA_PATH, sep=";")

        return df

    def calc_spread(self, price1, price2):
        prices = [price1, price2]
        max_p = max(prices)
        min_p = min(prices)
        spread = max_p - min_p
        spread_rate = spread / min_p

        return {"buy_price": min_p, "sell_price": max_p, "spread": spread, "spread_p": spread_rate}

    def calc_profit(self, price_buy, price_sell, buyfee, sellfee, volume=1):
        # Buy x BTC at price1 and apply trading fee
        cost = volume * price_buy
        cost += cost * buyfee
        # Sell x BTC at price 2 and apply trading fee
        income = volume * price_sell
        income -= income * sellfee
        # Convert to base currency and apply conversion surcharge
        profit = income - cost

        return profit

    def get_portfolio_value(self, quote="EUR", update=False):
        if update:
            self._update_balances()
            self._update_eur_balance()
        if quote == "EUR":
            total = self.coindf["Total_EUR_Balance"].sum()
            return total


class Trader(PortfolioManager):
    def get_arb_data(self, base, quote1="EUR", quote2="USD", report=False):
        if quote1 == "EUR" and quote2 == "USD":
            convrate = self.c.get_rate("USD", "EUR")
        else:
            convrate = self.get_best_bid(quote2, quote1)[1]

        bidask1 = self.get_all_ex_bid_ask(base, quote1)
        bidask2 = self.get_all_ex_bid_ask(base, quote2)

        arb_dict = {}
        convdict = {}
        for exchange in bidask1.keys():
            if exchange in bidask2.keys():
                convdict[exchange] = {
                    "ask": bidask2[exchange]["ask"] * convrate,
                    "bid": bidask2[exchange]["bid"] * convrate
                }

                asks = sorted([(quote1, bidask1[exchange]["ask"]), (quote2, convdict[exchange]["ask"])], key=lambda x: x[1])
                bids = sorted([(quote1, bidask1[exchange]["bid"]), (quote2, convdict[exchange]["bid"])], key=lambda x: x[1],
                              reverse=True)
                spread = bids[0][1] - asks[0][1]
                spread_rate = spread / asks[0][1]
                buyfee = self.get_trading_fee(exchange, base, quote=asks[0][0])
                sellfee = self.get_trading_fee(exchange, base, quote=bids[0][0])
                profit = self.calc_profit(asks[0][1], bids[0][1], buyfee, sellfee)

                if profit > 0:
                    arb_dict[exchange] = {
                        "base": base,
                        "buy_curr": asks[0][0],
                        "sell_curr": bids[0][0],
                        "buy_price": asks[0][1],
                        "sell_price": bids[0][1],
                        "spread": spread,
                        "profit": profit
                    }

                if report:
                    # TODO: Get precision to print with currency and exchange specific decimals
                    if asks[0][0] != bids[0][0]:
                        print("%s"
                              "Possible arbitrage on %s\n"
                              "Buy in %s price: %.5f\n"
                              "Sell in %s price: %.5f\n"
                              "Spread: %.2f %.2f%%\n"
                              "Profit: %.5f\n" %
                              (base, exchange, asks[0][0], asks[0][1], bids[0][0], bids[0][1], spread, spread_rate, profit))

        return arb_dict

    def btwn_ex_arb(self, base, quote, volume=None, report=False):
        bidask = self.get_all_ex_bid_ask(base, quote)
        exchanges = list(bidask.keys())
        ex_pairs = [comb for comb in combinations(exchanges, 2)]
        arb_dict = {}
        for pair in ex_pairs:
            asks = sorted([(pair[0], bidask[pair[0]]["ask"]), (pair[1], bidask[pair[1]]["ask"])], key=lambda x: x[1])
            bids = sorted([(pair[0], bidask[pair[0]]["bid"]), (pair[1], bidask[pair[1]]["bid"])], key=lambda x: x[1],
                          reverse=True)

            if asks[0][0] == bids[0][0]:
                if report:
                    print("No arbitrage possible between %s and %s." % (pair[0], pair[1]))

            else:
                if report:
                    if asks[0][1] == asks[1][1]:
                        print("Asks are equal")
                    if bids[0][1] == bids[1][1]:
                        print("Bids are euqal")

                spread = bids[0][1] - asks[0][1]
                spread_rate = spread / asks[0][1]
                buyfee = self.get_trading_fee(asks[0][0], base, quote=quote)
                sellfee = self.get_trading_fee(bids[0][0], base, quote=quote)
                wthdrwl = self.get_funding_fee(asks[0][0], base)[1]
                dpst = self.get_funding_fee(bids[0][0], base)[0]

                minvol = max([dpst, wthdrwl]) if dpst and wthdrwl else wthdrwl if wthdrwl else dpst if dpst else 0
                minvol = minvol * (1 + buyfee) * (1 + sellfee)

                if not volume or volume < minvol:
                    volume = minvol

                cost = volume * asks[0][1]
                cost += cost * buyfee
                sellvol = volume - wthdrwl if wthdrwl else volume
                sellvol = sellvol - dpst if dpst else sellvol
                income = sellvol * bids[0][1]
                income -= income * sellfee
                profit = income - cost

                if profit > 0:
                    arb_dict[pair] = {
                        "buyex": asks[0][0],
                        "sellex": bids[0][0],
                        "buyprice": asks[0][1],
                        "sellprice": bids[0][1],
                        "spread": spread
                        # "totalfees": wthdrwl + dpst + buyfee * volume + sellfee * income
                    }

                if report:
                    if profit > 0:
                        print("%s/%s\n"
                              "Possible arbitrage between %s and %s\n"
                              "Buy on %s for: %.5f\n"
                              "Sell on %s for: %.5f\n"
                              "Spread: %.2f (%.2f%%)\n"
                              "Profit: %.5f at volume %.5f\n" %
                              (base, quote, pair[0], pair[1], asks[0][0], asks[0][1], bids[0][0], bids[0][1], spread, spread_rate, profit, volume))
                    else:
                        print("No profitable arbitrage trade possible for %s/%s between %s and %s." % (base, quote, pair[0], pair[1]))

        return arb_dict

    def on_ex_arb_trade(self, base):
        # TODO: Make sure sold is available and the same as amount bought
        arb_dict = self.get_arb_data(base)
        if arb_dict:
            for exchange in arb_dict.keys():
                client = self.exchanges[exchange]["Client"]
                buy_quote = arb_dict[exchange]["buy_curr"]
                buy_price = arb_dict[exchange]["buy_price"]
                sell_quote = arb_dict[exchange]["sell_curr"]
                sell_price = arb_dict[exchange]["sell_price"]
                available_balance = client.fetch_balance()[buy_quote]["free"]
                amount = 0.75 * available_balance
                if available_balance:
                    order_id = self.limit_buy_order(exchange, base, buy_quote, amount, buy_price)
                    order_status = "open"
                    while order_status == "open":
                        order_status = self.get_order_status(exchange, order_id)
                        delay = int(client.rateLimit / 1000)
                        time.sleep(delay)
                    if order_status == "closed":
                        order_id = self.limit_sell_order(exchange, base, sell_quote, amount, sell_price)
                        return order_id
                else:
                    print("Not enough funds")

    def limit_buy_order(self, exchange, base, quote, amount, price):
        client = self.exchanges[exchange]["Client"]
        symbol = base + "/" + quote
        ex_base_symbols = self.coindf.loc[base, (exchange, "Base_Symbols")]
        if symbol in ex_base_symbols:
            order = client.create_limit_buy_order(symbol, amount, price)
            order_id = order["id"]
            return order_id
        else:
            print("Symbol not available on %s" % exchange)

    def limit_sell_order(self, exchange, base, quote, amount, price):
        client = self.exchanges[exchange]["Client"]
        symbol = base + "/" + quote
        ex_base_symbols = self.coindf.loc[base, (exchange, "Base_Symbols")]
        if symbol in ex_base_symbols:
            order = client.create_limit_sell_order(symbol, amount, price)
            order_id = order["id"]
            return order_id
        else:
            print("Symbol not available on %s" % exchange)

    def get_order_status(self, exchange, order_id):
        client = self.exchanges[exchange]["Client"]
        if client.has["fetchOrder"]:
            order = client.fetch_order(order_id)
            return order["status"]
        else:
            print("%s doesn't support fetch_order()")

    def query_order(self, exchange, order_id):
        client = self.exchanges[exchange]["Client"]
        if client.has["fetchOrder"]:
            order = client.fetch_order(order_id)
        else:
            order = None

        return order
