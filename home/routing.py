#from django.urls import re_path
from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    #path("ws/chat/", ChatConsumer.as_asgi()),
    path("ws/chat/<str:username>/", ChatConsumer.as_asgi()),
]
