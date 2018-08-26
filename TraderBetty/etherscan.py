"""Implementation of the etherscan.io API"""
import os
import json
from configparser import ConfigParser
import requests

# base url for own scrape
BASE_URL = "https://api.etherscan.io/api"
MODULE = "account"
PATH = "data"


class Scanner:
    def __init__(self, configfile, key_file):
        self.session = requests.Session()

        self.config = ConfigParser()

        if not os.path.isfile(configfile):
            raise ValueError

        self.config.read(configfile)
        self.config_addresses = self.config.get(
            'ether_wallet', 'addresses').split(',')

        self.API_KEY = self._get_api_key(key_file)

    def _get_api_key(self, key_file):
        # Load the api keys from keys file
        with open(key_file) as file:
            keys = json.load(file)
        api_key = keys["etherscan"]["apiKey"]
        return api_key

    def check_balance(self):
        addresses = self.config_addresses
        if not addresses:
            print("No valid addresses found. Aborting!")
            return None
        if len(addresses) > 1:
            action = "multibalance"
            addresses = ",".join(addresses)
        else:
            action = "balance"
            addresses = addresses[0]
        modact = "?module={:s}&action={:s}".format(MODULE, action)
        url = BASE_URL + modact + (
            "&address={:s}&tag=latest&apikey={:s}".format(
                addresses, self.API_KEY)
        )
        r = self.session.get(url)
        content = r.content.decode('utf-8', 'ignore')
        balances = json.loads(content)
        return balances
