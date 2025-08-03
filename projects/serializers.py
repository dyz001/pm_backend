from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'code',
            'git_url',
            'default_branch',
            'current_branch',
            'status',
            'auto_clone',
            'created_at'
        ]
        read_only_fields = ['id', 'current_branch', 'status', 'created_at']