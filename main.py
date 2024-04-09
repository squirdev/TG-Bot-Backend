import asyncio

from utils.websocket_utils import start_websocket_server


if __name__ == "__main__":
    asyncio.run(start_websocket_server())
