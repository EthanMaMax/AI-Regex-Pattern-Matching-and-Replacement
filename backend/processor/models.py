from uuid import uuid4

from django.db import models


class UploadedDataset(models.Model):
    dataset_id = models.UUIDField(default=uuid4, db_index=True)
    original_name = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=500, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_modified_at = models.DateTimeField(auto_now=True)
    row_count = models.PositiveIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.original_name} ({self.dataset_id})"
