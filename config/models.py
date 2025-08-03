from django.db import models

class Config(models.Model):
    editor_paths = models.JSONField(default=dict)
    projects_root = models.CharField(max_length=255)
    rsync_groups = models.JSONField(default=dict)
    output_root = models.CharField(max_length=255)
    ssh_keys = models.JSONField(default=list)
    log_directory = models.CharField(max_length=255)

    def __str__(self):
        return 'Global Configuration'