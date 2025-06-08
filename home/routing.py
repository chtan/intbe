#from django.urls import re_path
from django.urls import path
from .consumers import ChatConsumer, ChatConsumer0, ChatConsumer1, ChatConsumer2

websocket_urlpatterns = [
    #path("ws/chat/", ChatConsumer.as_asgi()),
    path("ws/chat/<str:username>/", ChatConsumer.as_asgi()),
    path("ws/chat/coordinator/<str:username>/", ChatConsumer1.as_asgi()),
    path("ws/chat/anonymous/<str:tasktoken>/", ChatConsumer2.as_asgi()),    
]
