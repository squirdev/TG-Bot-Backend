from web3 import Web3
from web3.middleware import geth_poa_middleware

from abi.UniswapFactoryV2 import factory_abi
from conf.constants import ETH_RPCS, UNI_V2_FACTORY_ADDR, WETH_ADDR, BSC_RPCS, PCS_V2_FACTORY_ADDR, WBNB_ADDR,SOL_RPCS

SEPOLIA_W3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/abc"))
ETH_W3 = Web3(Web3.HTTPProvider(ETH_RPCS[0]))
BSC_W3 = Web3(Web3.HTTPProvider(BSC_RPCS[0]))
SOL_W3 = Web3(Web3.HTTPProvider(SOL_RPCS[0]))

BSC_W3.middleware_onion.inject(geth_poa_middleware, layer=0)

PROVIDERS = {
    # 11155111: {
    #     "chainId": 11155111,
    #     "rpcs": ["https://sepolia.infura.io/v3/abc"],
    #     "index": 0,
    #     "w3": SEPOLIA_W3,
    #     "factory": SEPOLIA_W3.eth.contract(address=UNI_V2_FACTORY_SEPOLIA_ADDR, abi=factory_abi),
    #     "token": WETH_SEPOLIA_ADDR,
    #     "startBlock": 0,
    #     "scan": "https://etherscan.io",
    #     "blockIntervalSeconds": 30
    # },
    1: {
        "chainId": 1,
        "chainName": "eth",
        "rpcs": ETH_RPCS,
        "index": 0,
        "w3": ETH_W3,
        "factory": ETH_W3.eth.contract(address=UNI_V2_FACTORY_ADDR, abi=factory_abi),
        "token": WETH_ADDR,
        "startBlock": 18455061,
        "scan": "https://etherscan.io",
        "blockIntervalSeconds": 15
    },
    56: {
        "chainId": 56,
        "chainName": "bsc",
        "rpcs": BSC_RPCS,
        "index": 0,
        "w3": BSC_W3,
        "factory": BSC_W3.eth.contract(address=PCS_V2_FACTORY_ADDR, abi=factory_abi),
        "token": WBNB_ADDR,
        "startBlock": 33023647,
        "scan": "https://bscscan.com",
        "blockIntervalSeconds": 5,
        # "blockIntervalSeconds": 5,
    },
    900: {
        "chainId": 900,
        "chainName": "Solana",
        "rpcs": SOL_RPCS,
        "index": 0,
        "w3": SOL_W3,
        "factory": BSC_W3.eth.contract(address=PCS_V2_FACTORY_ADDR, abi=factory_abi),
        "token": WBNB_ADDR,
        "startBlock": 33023647,
        "scan": "https://solscan.io",
        "blockIntervalSeconds": 5,
        # "blockIntervalSeconds": 5,
    }
}
