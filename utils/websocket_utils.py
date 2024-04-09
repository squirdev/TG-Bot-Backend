import asyncio
import base64
import urllib
from datetime import datetime
import chardet
import requests
import websockets
import json
import urllib.request
from web3 import Web3
from conf.constants import BURN_ADDR
from conf.rpc_providers import PROVIDERS
from utils.swap_tracking_utils import init_tracking, add_to_tracking, remove_from_tracking, tracking_map, \
    tracking_blocks
from utils.auth_utils import validate_access
from utils.web3_utils import track_swaps, get_pair_address_for_tokens, is_token_0, get_decimals, get_symbol
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import borsh_construct as borsh
from urlextract import URLExtract
import re
from urllib.parse import urlparse

# SERVER

SAVING_BLOCKS_EACH = 100

SWAP_EVENTS = "swaps"
GET_SYMBOL_EVENT = "token_symbol"
ADD_TOKEN_EVENT = "add_token"
REMOVE_TOKEN_EVENT = "remove_token"
TX_HASH_CHECK_ROUNDS = 20

tasks = []

last_n_tx_hashes = {}
last_n_tx_hashes_round = 0


class Metadata(borsh.CStruct):
    name = borsh.String
    symbol = borsh.String


# Borsh schema for Metadata (simplified for name and symbol)
async def handle_get_symbol(websocket):
    data = None
    ret_msg = None

    try:
        token_data = json.loads(await websocket.recv())
        token_addr = Web3.to_checksum_address(token_data.get("address"))
        chain_id = token_data.get("chain")
        provider = PROVIDERS[chain_id]
        token_symbol = get_symbol(provider, token_addr)
        status = 200
        data = {'symbol': token_symbol}
    except Exception as e:
        ret_msg = e
        status = 400
        print(e)

    await websocket.send(json.dumps(
        {'status': status, 'message': ret_msg, 'data': data})
    )


METAPLEX_METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
TOKEN_MINT_ADDRESS = "YourTokenMintAddressHere"

# Initialize Solana client (pointing to mainnet)
client = Client("https://api.mainnet-beta.solana.com")


def get_metadata_account(mint_address):
    """Derive the Metadata account address."""
    mint_pubkey = Pubkey.from_string(mint_address)
    metadata_seeds = [b"metadata", Pubkey.from_string(METAPLEX_METADATA_PROGRAM).__bytes__(), mint_pubkey.__bytes__()]
    metadata_pubkey = \
        Pubkey.find_program_address(seeds=metadata_seeds, program_id=Pubkey.from_string(METAPLEX_METADATA_PROGRAM))[0]
    return metadata_pubkey


def find_str(s, char):
    index = 0

    if char in s:
        c = char[0]
        for ch in s:
            if ch == c:
                if s[index:index + len(char)] == char:
                    return index

            index += 1

    return -1


def extract_urls_with_regex(text):
    pattern = r'(https?://)?([a-zA-Z\d.-]+)\.([a-z.]{2,6})'
    return re.findall(pattern, text)


def extract_urls(text):
    url_pattern = r'https?://\S+'
    return re.findall(url_pattern, text)


def remove_non_ascii(s):
    return s.encode('ascii', 'ignore').decode()


def fetch_metadata(mint_address):
    # """Fetch and parse token metadata from the Metaplex Metadata account."""
    # metadata_account = get_metadata_account(mint_address)
    # account_info = json.loads(client.get_account_info(metadata_account).to_json())['result']['value']
    # data = base64.b64decode(account_info['data'][0])
    # # Detect encoding
    # detected = chardet.detect(data)
    # encoding = detected['encoding']
    # # decoded_data = data.decode(encoding)
    # # print(detected)
    # extractor = URLExtract()
    # detected_string = data.decode(encoding, errors="ignore")
    # urls = extract_urls(detected_string)
    #
    # extracted_string = remove_non_ascii(urls[0])
    # # Print the filtered URLs
    #
    # print(extracted_string)
    #
    # start = find_str(detected_string, 'https')
    # end = find_str(detected_string, '.link')
    # link = detected_string[start:end + 5]
    # print(link)
    print('https://api.solana.fm/v1/tokens/'+mint_address)
    meta_info = requests.get('https://api.solana.fm/v1/tokens/'+mint_address)
    result = json.loads(meta_info.content)["tokenList"]
    # result = json.loads(meta_info.read())
    # print(result['name'])
    # print(result['symbol'])
    return [result['name'], result['symbol']]


async def handle_add_token(websocket):
    global metadata
    data = None
    try:
        new_token_data = json.loads(await websocket.recv())
        chain_id = new_token_data.get("chain")
        print(chain_id)
        provider = PROVIDERS[chain_id]
        if chain_id == 900:
            token_addr = new_token_data.get("address")
        else:
            token_addr = Web3.to_checksum_address(new_token_data.get("address"))

        if chain_id == 900:
            metadata = fetch_metadata(token_addr)
            print(metadata)
            token_info = json.loads(client.get_token_supply(Pubkey.from_string(token_addr)).to_json())
            token_decimals = token_info['result']['value']['decimals']
        else:
            token_decimals = get_decimals(provider, token_addr)

        print(token_decimals)
        paired_token_addr = new_token_data.get("paired")
        ret_msg = "Successfully added token"

        if chain_id == 900:
            status = 200
            print(ret_msg)
            data = {'symbol': metadata[1], 'address': token_addr}
            added = add_to_tracking(
                chain_id,
                metadata[1],
                token_decimals,
                "",
                token_addr,
                "",
                ""
            )

            if not added:
                raise Exception("Unexpected error")
        else:
            print(paired_token_addr)
            status = 200
            print(ret_msg)
            if paired_token_addr is None:
                paired_token_addr = provider.get("token")
            else:
                paired_token_addr = Web3.to_checksum_address(paired_token_addr)

            token_symbol = get_symbol(provider, token_addr)
            paired_token_decimals = get_decimals(provider, paired_token_addr)
            pair_addr = get_pair_address_for_tokens(provider, token_addr, paired_token_addr)

            if pair_addr == BURN_ADDR:
                print("Pair not found")

                await websocket.send(json.dumps({'status': 400, 'message': 'Pair not found'}))

                return

            token_is_token_0 = is_token_0(token_addr, paired_token_addr)

            added = add_to_tracking(
                chain_id,
                token_symbol,
                token_decimals,
                paired_token_decimals,
                token_addr,
                pair_addr,
                token_is_token_0,
            )

            if not added:
                raise Exception("Unexpected error")

            data = {'symbol': token_symbol, 'address': token_addr}
    except Exception as e:
        ret_msg = e
        status = 400
        print(e)

    await websocket.send(json.dumps(
        {'status': status, 'message': ret_msg, 'data': data})
    )

    print("Closed single call")


async def handle_remove_token(websocket):
    removal_data = json.loads(await websocket.recv())

    removed = remove_from_tracking(removal_data['chain'], removal_data['address'])

    await websocket.send(json.dumps({'status': 'removed' if removed else 'failed'}))

    print("Closed single call")


prev_data = None


async def listen_swap_events(provider, websocket):
    global client
    global last_n_tx_hashes
    global last_n_tx_hashes_round

    last_block = 0

    while True:
        if client is None:
            await asyncio.sleep(provider.get("blockIntervalSeconds"))

            continue

        try:
            chain = provider.get("chainId")

            if last_block == 0:
                last_block = tracking_blocks.get(chain, 0)

            targets = tracking_map.get(chain, {}).items()

            if last_block is not None:
                (swaps, new_last_block) = track_swaps(provider, last_block, targets, last_n_tx_hashes)

                for token in swaps.keys():
                    for tx in swaps.get(token).get("txs"):
                        last_n_tx_hashes[tx.get("txHash")] = True

                if len(swaps) > 0:
                    if last_n_tx_hashes_round == TX_HASH_CHECK_ROUNDS:
                        last_n_tx_hashes = {}
                        last_n_tx_hashes_round = 0

                    last_n_tx_hashes_round += 1

                    print(f"[{datetime.now()}] Catch events for chain {chain}, sending data")
                    message = json.dumps({"data": {'chain': chain, 'events': swaps}})

                    await client.send(message)

                last_block = new_last_block
        except Exception as e:
            print(e)

        await asyncio.sleep(provider.get("blockIntervalSeconds"))


async def unified_handler(websocket):
    global client
    global tasks

    try:
        auth_token = await websocket.recv()
        print(auth_token)
        if not validate_access(auth_token):
            return

        print("Successfully connected!")
    except:
        return

    event_type = await websocket.recv()

    if event_type == GET_SYMBOL_EVENT:
        await handle_get_symbol(websocket)
    elif event_type == ADD_TOKEN_EVENT:
        await handle_add_token(websocket)
    elif event_type == REMOVE_TOKEN_EVENT:
        await handle_remove_token(websocket)
    elif event_type == SWAP_EVENTS:
        # restricted to a single event listener client
        if client is not None:
            print("Connection refused: another client is already connected.")

            await websocket.close()

            return

        client = websocket

        if len(tasks) == 0:
            for provider in PROVIDERS.values():
                tasks.append(asyncio.create_task(listen_swap_events(provider, websocket)))

        try:
            while True and client is not None:
                pong_waiter = await websocket.ping()

                await pong_waiter
                await asyncio.sleep(10)
        except Exception as e:
            if client is not None:
                print(e)

                await client.close()

                client = None
                print("Connection closed!")


async def start_websocket_server():
    init_tracking()

    server = await websockets.serve(unified_handler, "0.0.0.0", 4000, ping_interval=20, ping_timeout=20)

    await server.wait_closed()


# CLIENT examples below

uri = "ws://84.32.41.30:4000"
api_key = "Ad82d2Ffezuy70G00-2NbwVo5f60Aiy"  # must be in database so it can validate this key


async def subscribe(event):
    async with websockets.connect(uri) as websocket:
        # auth
        await websocket.send(api_key)

        await websocket.send(event)

        while True:
            response = await websocket.recv()
            print(json.loads(response))


async def add_token(chain, address, paired_token, min_swap=0):
    async with websockets.connect(uri) as websocket:
        await websocket.send(api_key)
        await websocket.send('add_token')

        new_token_data = {
            'chain': chain,
            'address': address,
            'paired': paired_token,
        }
        await websocket.send(json.dumps(new_token_data))

        response = await websocket.recv()

        return json.loads(response)


async def remove_token(chain, address):
    async with websockets.connect(uri) as websocket:
        await websocket.send(api_key)
        await websocket.send('remove_token')

        removal_data = {'chain': chain, 'address': address}

        await websocket.send(json.dumps(removal_data))

        response = await websocket.recv()

        return json.loads(response)
