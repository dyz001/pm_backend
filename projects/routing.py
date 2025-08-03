from django.urls import re_path
from .consumers import LogConsumer

websocket_urlpatterns = [
    # 客户端通过 ws://<host>/ws/logs/<task_id>/ 订阅日志输出
    re_path(r'^ws/logs/(?P<task_id>[0-9a-f-]+)/$', LogConsumer.as_asgi()),
]