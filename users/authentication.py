from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from bson import ObjectId
#import pymongo
from django.conf import settings
from datetime import datetime
from mongoengine.connection import get_db


class DummyUser:
    def __init__(self, id):
        self.id = id
        self.is_active = True

    @property
    def is_authenticated(self):
        return True

class MongoJWTAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.client = pymongo.MongoClient(settings.MONGO_URI)
        #self.db = self.client[settings.MONGO_DB_NAME]
        #self.users = self.db["users"]
        #self.blacklist = self.db["blacklisted_tokens"]
        self.users = get_db()["users"]
        self.blacklist = get_db()["blacklisted_tokens"]

    def get_user(self, validated_token):
        user_id = validated_token.get(settings.SIMPLE_JWT['USER_ID_CLAIM'])
        if user_id is None:
            return None
        user_doc = self.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return None

        return DummyUser(str(user_doc["_id"]))

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)

        jti = token.get("jti")
        if jti and self.blacklist.find_one({"jti": jti}):
            raise InvalidToken("Token has been blacklisted")

        return token


    #def authenticate(self, request):
    #    """
    #    https://github.com/jazzband/djangorestframework-simplejwt/blob/master/rest_framework_simplejwt/authentication.py
    #    """
    #    print("MongoJWTAuthentication.authenticate() called")
    #    return super().authenticate(request)

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token


class AnonymousTokenAuthentication(BaseAuthentication):
    def __init__(self):
        self.collection = get_db()["anon_tokens"]
        #client = pymongo.MongoClient(settings.MONGO_URI)
        #self.collection = client[settings.MONGO_DB_NAME]["anon_tokens"]

    def authenticate(self, request):
        """
        The logic for allowed_endpoints has not been coded here.
        """
        token = request.headers.get("X-Anonymous-Token")
        if not token:
            return None  # Let other authentication handle it

        token_doc = self.collection.find_one({"token": token})
        if not token_doc:
            raise AuthenticationFailed("Invalid anonymous token")

        if token_doc.get("expires_at") and datetime.utcnow() > token_doc["expires_at"]:
            raise AuthenticationFailed("Anonymous token expired")

        if token_doc.get("used", False):
            raise AuthenticationFailed("Anonymous token already used")

        # Mark as used if single-use
        if token_doc.get("single_use", False):
            self.collection.update_one({"_id": token_doc["_id"]}, {"$set": {"used": True}})

        # Create a dummy user-like object for permission checks
        return (AnonymousUser(token=token), None)

class AnonymousUser:
    def __init__(self, token):
        self.token = token
        self.is_authenticated = False
        self.is_anonymous_token = True
