from django.db import models


class Project(models.Model):
    title = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50)
    git_url = models.URLField()
    default_branch = models.CharField(max_length=100, default='master')
    current_branch = models.CharField(max_length=100, blank=True)
    local_path = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('NotCloned', 'NotCloned'),
            ('UpToDate', 'UpToDate'),
            ('Modified', 'Modified'),
            ('Behind', 'Behind')
        ],
        default='NotCloned'
    )
    auto_clone = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title