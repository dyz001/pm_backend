from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from projects.views import ProjectViewSet
from config.views import ConfigViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'config', ConfigViewSet, basename='config')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),         # 注册 /api/projects/ 等
    path('api/config/', include('config.urls')), # 注册 /api/config/
]
