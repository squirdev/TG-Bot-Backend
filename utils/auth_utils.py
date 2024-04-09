from utils.mongo_utils import api_key_collection


def validate_access(api_key):
    return api_key_collection.find_one().get("secret") == api_key
