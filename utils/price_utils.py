import time

from moralis import evm_api

from conf.constants import MORALIS_API_KEY
from conf.rpc_providers import PROVIDERS

# Each 30 min, might adapt, probably add moralis keys here at some point
FETCH_INTERVAL_SEC = 1800

prices = {
    "last_fetch": 0
}

token_prices = {

}

PARAMS = {
    key: {
      "chain": val.get("chainName"),
      "address": val.get("token")
    } for key, val in PROVIDERS.items()
}


def get_prices():
    last_fetch = prices.get("last_fetch")
    now = int(time.time())

    if now > last_fetch + FETCH_INTERVAL_SEC:
        for key, param in PARAMS.items():
            res = evm_api.token.get_token_price(
                api_key=MORALIS_API_KEY,
                params=param,
            )

            prices[key] = res.get("usdPrice")

        prices["last_fetch"] = now

    return prices


def get_price(chain):
    fetched = get_prices()

    return fetched.get(chain)


def get_token_price(chain, addr):
    last_fetch = token_prices.get(chain, {}).get(addr, {}).get("last_fetch", 0)
    now = int(time.time())

    if now > last_fetch + FETCH_INTERVAL_SEC:
        try:
            res = evm_api.token.get_token_price(
                api_key=MORALIS_API_KEY,
                params={
                    "chain": PROVIDERS[chain].get("chainName"),
                    "address": addr
                },
            )

            if token_prices.get(chain) is None:
                token_prices[chain] = {}

            token_prices[chain][addr] = {
                "price": res.get("usdPrice"),
                "last_fetch": now
            }
        except Exception as e:
            print("Error fetching token price", e)

            return None

    if token_prices.get(chain).get(addr):
        return token_prices.get(chain).get(addr).get("price")
