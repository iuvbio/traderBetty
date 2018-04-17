#!/usr/bin/env python3
"""
Main executable
"""

import os
import sys
import time
import json
from TraderBetty.TraderBetty.betty import Trader as Tb

here = os.path.abspath("TraderBetty/TraderBetty")
root = os.path.dirname(here)
config = os.path.join(root, "config.ini")
keys_file = os.path.join(root, "keys.json")

betty = Tb(config_path=config, api_path=keys_file)


def main(sleeptime=10):
    try:
        while True:
            betty.get_arb_data("BTC")
            time.sleep(sleeptime)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    status = main()
    sys.exit(status)
