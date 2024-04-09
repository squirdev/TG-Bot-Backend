from web3 import Web3
from abi.UniswapPairV2 import *
from abi.ERC20 import *
from web3.middleware import geth_poa_middleware

from utils.price_utils import get_token_price


MAX_BLOCKS_FETCH = 10


def switch_provider(provider_dict):
    rpcs = provider_dict['rpcs']
    next_index = (provider_dict['index'] + 1) % len(rpcs)
    provider_dict['index'] = next_index
    new_rpc = rpcs[next_index]

    if provider_dict.get("chainId") == 56:
        provider = Web3(Web3.HTTPProvider(new_rpc))
        provider.middleware_onion.inject(geth_poa_middleware, layer=0)

        provider_dict['w3'] = provider
    else:
        provider_dict['w3'] = Web3(Web3.HTTPProvider(new_rpc))


def safe_web3_call(call_fn, *args, **kwargs):
    provider_dict = kwargs.pop("provider_dict", None)
    try:
        return call_fn(*args, **kwargs)
    except:
        if provider_dict:
            switch_provider(provider_dict)
        return call_fn(*args, **kwargs)


def get_pair_address_for_tokens(provider, token1_address, token2_address):
    get_pair_method = provider["factory"].functions.getPair

    if token2_address is None:
        token2_address = provider['token']

    pair_address = None

    try:
        pair_address = safe_web3_call(get_pair_method(token1_address, token2_address).call, provider_dict=provider)
    except Exception as e:
        print(f"An error occurred: {e}")

    return pair_address


def get_symbol(provider, token_addr):
    erc20_contract = provider.get("w3").eth.contract(address=token_addr, abi=erc20_abi)
    symbol_method = erc20_contract.functions.symbol

    return safe_web3_call(symbol_method().call, provider_dict=provider)


def get_name(provider, token_addr):
    erc20_contract = provider.get("w3").eth.contract(address=token_addr, abi=erc20_abi)
    name_method = erc20_contract.functions.name

    return safe_web3_call(name_method().call, provider_dict=provider)


def get_decimals(provider, token_addr):
    erc20_contract = provider.get("w3").eth.contract(address=token_addr, abi=erc20_abi)
    decimals_method = erc20_contract.functions.decimals

    return safe_web3_call(decimals_method().call, provider_dict=provider)


def parse_unit_value(value, decimals):
    return round(value / pow(10, decimals), 3)


def is_token_0(expected_0, expected_1):
    return expected_0.lower() < expected_1.lower()


def track_swaps(provider, last_block, targets, last_n_tx_hashes):
    new_last_block = provider['w3'].eth.get_block('latest').number

    if last_block >= new_last_block:
        print("from block greater equals latest")
        return {}, last_block

    from_block = last_block if last_block else new_last_block

    swaps = {}

    print("Checking", provider.get("chainName"), "events from block", from_block, "to block", new_last_block,
          "with delta", new_last_block - from_block)

    for address, details in targets:
        if details is None:
            continue

        swap_data = {
            "symbol": details.get("symbol"),
            "address": address,
            "txs": []
        }

        pair_contract = provider.get("w3").eth.contract(address=details['pair'], abi=pair_abi)

        used_tx_ids = {}

        try:
            events = pair_contract.events.Swap().get_logs(fromBlock=from_block)
        except Exception as e:
            print(e)

            try:
                switch_provider(provider)
                pair_contract = provider.get("w3").eth.contract(address=details['pair'], abi=pair_abi)
                events = pair_contract.events.Swap().get_logs(fromBlock=from_block)
            except Exception as e2:
                print(e2)
                print("Issue with both providers, skipping")
                return

        token_price = None

        if len(events) > 0:
            token_price = get_token_price(provider.get("chainId"), address)

        for event in events:
            tx_id = event.transactionHash.hex()

            if used_tx_ids.get(tx_id) is not None or last_n_tx_hashes.get(tx_id):
                continue
            else:
                used_tx_ids[tx_id] = True

            if details.get("isToken0"):
                purchased = event.args.amount0Out
                swapped = event.args.amount1In
            else:
                purchased = event.args.amount1Out
                swapped = event.args.amount0In

            if purchased > 0:
                tokens_purchased = parse_unit_value(purchased, details.get("decimals"))

                swap_data.get("txs").append({
                    "txHash": tx_id,
                    "purchased": tokens_purchased,
                    "token_price": token_price,
                    "swapped": parse_unit_value(swapped, details.get("pairedDecimals")),
                    "taker": event.args.to
                })

        # here we won't notify if there's nothing
        if len(swap_data.get("txs")) > 0:
            swaps[address] = swap_data

    return swaps, new_last_block + 1
