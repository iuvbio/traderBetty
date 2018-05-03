#!/usr/bin/env python3
"""
Main executable
"""

import os
import sys
import time
from . import betty

here = os.path.abspath("TraderBetty/TraderBetty")
root = os.path.dirname(here)
config = os.path.join(root, "config.ini")
keys_file = os.path.join(root, "keys.json")

# TODO: include possibility to input api and config path
trader = betty.Trader(config_path=config, api_path=keys_file)


def main(sleeptime=10):
    try:
        while True:
            trader.on_ex_arb_trade("BTC")
            time.sleep(sleeptime)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    status = main()
    sys.exit(status)
