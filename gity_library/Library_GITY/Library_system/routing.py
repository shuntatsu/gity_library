from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from . import consumers

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    re_path(r"ws/some_path/$", consumers.YourConsumer.as_asgi()),
                ]
            )
        ),
    }
)
