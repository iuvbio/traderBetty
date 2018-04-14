#!/usr/bin/env python3
"""
Main executable
"""

import time
import sys
from .betty import Trader as Tb


betty = Tb(input("API Path: "), input("Wallet file: "))


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
