"""
ASGI config for Library_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Library_system.settings')

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # ルーティング設定（今回はURLRouterを使用）
        "websocket": AuthMiddlewareStack(
            URLRouter(
                # ここにWebSocketのルーティングを追加できる
            )
        ),
    }
)

