import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import django

django.setup()

from django.core.asgi import get_asgi_application
import projects.routing  # 假设日志 WebSocket 路由在此定义

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_manager.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            projects.routing.websocket_urlpatterns
        )
    ),
})