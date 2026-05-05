from django.urls import path

from .views import (
    DatasetDetailView,
    DatasetRedoView,
    DatasetUndoView,
    DownloadDatasetView,
    NaturalLanguageReplaceView,
    ReplacePreviewView,
    UploadPreviewView,
)


urlpatterns = [
    path("upload/", UploadPreviewView.as_view(), name="upload-preview"),
    path("replace/", ReplacePreviewView.as_view(), name="replace-preview"),
    path(
        "natural-language-replace/",
        NaturalLanguageReplaceView.as_view(),
        name="natural-language-replace",
    ),
    path("download/<str:dataset_id>/", DownloadDatasetView.as_view(), name="download-dataset"),
    path("datasets/<str:dataset_id>/", DatasetDetailView.as_view(), name="dataset-detail"),
    path("datasets/<str:dataset_id>/undo/", DatasetUndoView.as_view(), name="dataset-undo"),
    path("datasets/<str:dataset_id>/redo/", DatasetRedoView.as_view(), name="dataset-redo"),
]
