import pymongo
from django.conf import settings


dbclient = pymongo.MongoClient(settings.MONGO_URI)
db = dbclient[settings.MONGO_DB_NAME]
blacklist_collection = db["blacklisted_tokens"]


def is_token_blacklisted(jti):
    return blacklist_collection.find_one({"jti": jti}) is not None

