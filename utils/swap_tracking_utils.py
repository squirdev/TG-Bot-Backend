from utils.mongo_utils import tracking_collection

tracking_map = {}

tracking_blocks = {}


def init_tracking():
    tracking_map.clear()

    try:
        tracking_list = tracking_collection.find()

        for elt in tracking_list:
            chain = elt.get("chain")

            if tracking_map.get(chain) is None:
                tracking_map[chain] = {}

            tracking_map[chain][elt.get("address")] = {
                "symbol": elt.get("symbol"),
                "decimals": elt.get("decimals"),
                "pairedDecimals": elt.get("pairedDecimals"),
                "chain": chain,
                "used": elt.get("used"),
                "address": elt.get("address"),
                "pair": elt.get("pair"),
                "isToken0": elt.get("isToken0")
            }

            tracking_blocks[chain] = 0
    except Exception as error:
        print(error)


def add_to_tracking(chain, symbol, decimals, other_decimals, address, pair, is_token_0):
    added = False

    if tracking_map.get(chain) is None:
        tracking_map[chain] = {}

    prev = tracking_map.get(chain).get(address)

    if prev is None:
        elt = {
            "symbol": symbol,
            "decimals": decimals,
            "pairedDecimals": other_decimals,
            "chain": chain,
            "used": 1,
            "address": address,
            "pair": pair,
            "isToken0": is_token_0
        }

        try:
            tracking_collection.insert_one(elt)
            tracking_map[chain][address] = elt

            added = True
        except Exception as error:
            print(error)
    else:
        prev["used"] += 1

        try:
            tracking_collection.update_one(
                {"chain": chain, "address": address},
                {"$inc": {"used": 1}}
            )

            added = True
        except Exception as error:
            print(error)

    return added


def remove_from_tracking(chain, address):
    removed = False

    prev = tracking_map.get(chain, {}).get(address)

    if prev is not None:
        prev["used"] -= 1

        if prev["used"] <= 0:
            try:
                tracking_collection.delete_one({"chain": chain, "address": address})

                del tracking_map[chain][address]

                removed = True
            except Exception as error:
                print(error)
        else:
            try:
                tracking_collection.update_one(
                    {"chain": chain, "address": address},
                    {"$inc": {"used": -1}}
                )

                removed = True
            except Exception as error:
                print(error)

    return removed


def list_tracking(chain, address):
    if tracking_map[chain][address] is None:
        return ""

    output = []
    for address, details in tracking_map[chain].items():
        if details is None:
            continue

        symbol = details['symbol']
        pair = details['pair']
        output.append(f"Symbol: {symbol}, Address: {address}, Pair: {pair}")

    return "\n".join(output)
