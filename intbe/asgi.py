"""
ASGI config for intbe project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack # This does not work for JWT, hence need custom authorization.
from home.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "intbe.settings")

# OriginValidator is more fine-grained.
application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # HTTP requests
    #"websocket": URLRouter(websocket_urlpatterns),  # WebSocket routing    
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    ),
    #"websocket": AuthMiddlewareStack(
    #    URLRouter(websocket_urlpatterns)
    #),
})
