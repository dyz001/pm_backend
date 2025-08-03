from rest_framework import viewsets
from .models import Config
from .serializers import ConfigSerializer

class ConfigViewSet(viewsets.ModelViewSet):
    queryset = Config.objects.all()
    serializer_class = ConfigSerializer