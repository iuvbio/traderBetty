#!/usr/bin/env python3
"""
Wrapper for trading on different crypto exchanges using the ccxt library
"""

import time
import sys
import TraderBetty.betty as tb


betty = tb.Trader(input("API Path: "), input("Wallet file: "))


def main(sleeptime=10):
    try:
        while True:
            betty.get_arb_data("BTC")
            time.sleep(sleeptime)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    status = main()
    sys.exit(status)
