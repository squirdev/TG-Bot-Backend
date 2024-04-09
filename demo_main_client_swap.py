import asyncio

from utils.websocket_utils import subscribe

asyncio.get_event_loop().run_until_complete(subscribe("swaps"))
