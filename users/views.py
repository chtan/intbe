from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError
from rest_framework import status
from django.conf import settings
from datetime import datetime, timedelta
import jwt
import pymongo
from django.contrib.auth.hashers import check_password
from .authentication import DummyUser
from django.utils import timezone
import uuid
from .utils import is_token_blacklisted
from rest_framework.status import (
    HTTP_400_BAD_REQUEST, 
    HTTP_401_UNAUTHORIZED, 
    HTTP_200_OK, 
    HTTP_500_INTERNAL_SERVER_ERROR
)


# MongoDB setup
dbclient = pymongo.MongoClient(settings.MONGO_URI)
db = dbclient[settings.MONGO_DB_NAME]
users_collection = db["users"]
blacklist_collection = db["blacklisted_tokens"]

"""
class CustomTokenView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = users_collection.find_one({"username": username})

        if not user:
            return Response({"detail": "Invalid credentials"}, status=401)

        if not check_password(password, user.get("password")):
            return Response({"detail": "Invalid credentials"}, status=401)

        refresh = RefreshToken.for_user(DummyUser(user['_id']))
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })
"""

class RefreshTokenView(APIView):
    """
    This should not be protected by authentication, otherwise the logged-in user may be stuck.

    Instead, authentication can occur here.

    See post below suggested by ChatGPT.
    """
    def post(self, request):
        refresh_token = request.data.get("refresh")

        try:
            refresh = RefreshToken(refresh_token)

            if is_token_blacklisted(refresh["jti"]):
                return Response({"detail": "Token blacklisted"}, status=401)

            access = refresh.access_token
            return Response({"access": str(access)})

        except TokenError:
            return Response({"detail": "Invalid token"}, status=401)

    """
    def post(self, request):
        refresh_token = request.data.get("refresh")

        try:
            # Verify and decode refresh token manually
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            # Optional: check for blacklisted or revoked token here
            user = get_user_model().objects.get(id=user_id)

            # Generate new access token
            new_access_token = generate_access_token(user)

            return Response({"access": new_access_token}, status=HTTP_200_OK)

        except jwt.ExpiredSignatureError:
            return Response({"error": "Refresh token expired"}, status=HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token"}, status=HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"error": "Token refresh failed"}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    """


class LoginView(APIView):
    """
    With JWT authentication, the server typically does not need to register that the user has logged in.
    """
    authentication_classes = []  # Login doesn't require auth
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "Username and password required"}, status=400)

        user = users_collection.find_one({"username": username})
        if not user:
            return Response({"detail": "Invalid credentials"}, status=HTTP_401_UNAUTHORIZED)

        if not check_password(password, user.get("password", "")):
            return Response({"detail": "Invalid credentials"}, status=HTTP_401_UNAUTHORIZED)

        # Create tokens
        dummy_user = DummyUser(str(user["_id"]))
        refresh = RefreshToken.for_user(dummy_user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


class LogoutView(APIView):
    """
    Blacklisting occurs here
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            jti = token["jti"]

            # Blacklist it (store the JTI + expiry)
            blacklist_collection.insert_one({
                "jti": jti,
                "exp": token["exp"],
                "blacklisted_at": datetime.utcnow()
            })

            return Response({"detail": "Logout successful"}, status=HTTP_200_OK)

        except TokenError:
            return Response({"detail": "Invalid or expired token"}, status=HTTP_400_BAD_REQUEST)

