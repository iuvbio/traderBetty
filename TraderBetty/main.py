#!/usr/bin/env python3
"""
Main executable
"""

import os
import sys
import time
import argparse
"""
from TraderBetty.managers import config, handlers, portfolio
from TraderBetty.strategies import arbitrage
from TraderBetty import trader
"""
# Take care of paths
here = os.path.abspath("TraderBetty/TraderBetty")
root = os.path.dirname(here)
CONF = os.path.join(root, "config.ini")
KEYS = os.path.join(root, "keys.json")

# TODO: include possibility to input api and config path
connection_conf = config.ConnectionConfigLoader
full_conf = config.FullConfigLoader

CH = handlers.ConnectionHandler(CONF, connection_conf, KEYS)


def main():
    PM = portfolio.PortfolioManager(CH, CONF, full_conf)
    strategy = arbitrage.OnExchangeArbitrageStrategy()
    mytrader = trader.ArbitrageTrader(PM, strategy)
    try:
        while True:
            delay = int(mytrader.exchanges["bitstamp"].rateLimit / 1000)
            data = mytrader.get_data("bitstamp", "BTC", "EUR", "USD")
            print(data)
            time.sleep(delay)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # Create an argument passer for command line usage
    parser = argparse.ArgumentParser(description="TraderBetty will show you"
                                                 "what you got and even trade"
                                                 "for you!")
    parser.add_argument("-c", "--config", default=CONF)
    parser.add_argument("-k", "--keys", default=KEYS)
    status = main()
    sys.exit(status)
