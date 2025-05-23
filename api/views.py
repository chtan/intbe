from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import get_authorization_header
from rest_framework_simplejwt.authentication import JWTAuthentication
from jwt import decode as jwt_decode, InvalidTokenError
from django.conf import settings


class EchoView(APIView):
    permission_classes = [IsAuthenticated]  # Requires valid JWT
    #permission_classes = []

    def get(self, request):
        return Response({"message": "Hello from EchoView!"})


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission

class IsAnonymousTokenUser(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_anonymous_token", False)

class AnonDataView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):
        return Response({"message": "Welcome, anonymous user!"})