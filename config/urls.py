from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfigViewSet

router = DefaultRouter()
router.register(r'config', ConfigViewSet, basename='config')

urlpatterns = [
    path('api/', include(router.urls)),
]