from pymongo import MongoClient
from conf.constants import MONGO_CONNECT_URL, MONGO_DB, TRACKING_COLLECTION, TRACKING_BLOCK_COLLECTION,  API_KEY_COLLECTION

mongo_client = MongoClient(MONGO_CONNECT_URL)[MONGO_DB]

tracking_collection = mongo_client[TRACKING_COLLECTION]
tracking_blocks_collection = mongo_client[TRACKING_BLOCK_COLLECTION]
api_key_collection = mongo_client[API_KEY_COLLECTION]
