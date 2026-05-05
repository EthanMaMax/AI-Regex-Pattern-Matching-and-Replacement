from pathlib import Path
from io import BytesIO, StringIO
import json
import re
from datetime import timedelta
from uuid import uuid4

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import get_valid_filename
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .llm import MissingOpenAIKeyError, RegexPlanError, RegexPlanProviderError, generate_regex_plan
from .models import UploadedDataset
from .storage import (
    delete_dataframe,
    history_counts,
    load_dataframe,
    push_undo_state,
    redo_dataframe,
    save_dataframe,
    undo_dataframe,
)


SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
PREVIEW_ROW_LIMIT = 50


class UploadPreviewView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        cleanup_expired_datasets()

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "No file was uploaded. Use form field name 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            return Response(
                {
                    "detail": "Unsupported file type. Upload a CSV, XLS, or XLSX file.",
                    "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dataframe = self._read_uploaded_file(uploaded_file, extension)
        except EmptyDataError:
            return Response(
                {"detail": "The uploaded file is empty or has no readable columns."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ParserError as exc:
            return Response(
                {"detail": f"Could not parse the uploaded file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Could not read the uploaded file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(dataframe.columns) == 0:
            return Response(
                {"detail": "The uploaded file does not contain any columns."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if dataframe.empty:
            return Response(
                {"detail": "The uploaded file does not contain any rows."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataframe = dataframe.where(pd.notnull(dataframe), None)
        dataset_id = uuid4()
        try:
            storage_path = save_dataframe(dataset_id, dataframe)
            UploadedDataset.objects.create(
                dataset_id=dataset_id,
                original_name=uploaded_file.name,
                storage_path=str(storage_path),
                row_count=len(dataframe.index),
                column_count=len(dataframe.columns),
            )
        except OSError as exc:
            return Response(
                {"detail": f"Could not store the uploaded dataset: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Could not save dataset metadata: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        row_count = len(dataframe.index)
        column_count = len(dataframe.columns)

        return Response(
            {
                "dataset_id": str(dataset_id),
                "filename": uploaded_file.name,
                "columns": [str(column) for column in dataframe.columns],
                "row_count": row_count,
                "column_count": column_count,
                "preview_limit": PREVIEW_ROW_LIMIT,
                "can_undo": False,
                "can_redo": False,
                "preview": dataframe.head(PREVIEW_ROW_LIMIT).to_dict(orient="records"),
            },
            status=status.HTTP_201_CREATED,
        )

    def _read_uploaded_file(self, uploaded_file, extension):
        if extension == ".csv":
            return pd.read_csv(uploaded_file)
        return pd.read_excel(uploaded_file, engine="openpyxl" if extension == ".xlsx" else None)


class ReplacePreviewView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        column = request.data.get("column")
        pattern = request.data.get("regex")
        replacement = request.data.get("replacement", "")

        missing_fields = [
            field
            for field, value in {
                "dataset_id": dataset_id,
                "column": column,
                "regex": pattern,
            }.items()
            if not value
        ]
        if missing_fields:
            return Response(
                {"detail": f"Missing required field(s): {', '.join(missing_fields)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataframe, error_response = get_dataset_or_error(dataset_id)
        if error_response:
            return error_response

        if column not in dataframe.columns:
            return Response(
                {
                    "detail": f"Column '{column}' was not found in this dataset.",
                    "columns": [str(existing_column) for existing_column in dataframe.columns],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            compiled_pattern = re.compile(pattern)
        except re.error as exc:
            return Response(
                {"detail": f"Invalid regex: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = apply_replacement(dataframe, dataset_id, [column], compiled_pattern, replacement)

        return Response(result)


class NaturalLanguageReplaceView(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        dataset_id = request.data.get("dataset_id")
        natural_language = request.data.get("natural_language")

        missing_fields = [
            field
            for field, value in {
                "dataset_id": dataset_id,
                "natural_language": natural_language,
            }.items()
            if not value
        ]
        if missing_fields:
            return Response(
                {"detail": f"Missing required field(s): {', '.join(missing_fields)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataframe, error_response = get_dataset_or_error(dataset_id)
        if error_response:
            return error_response

        try:
            plan = generate_regex_plan(natural_language, dataframe.columns)
        except MissingOpenAIKeyError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except RegexPlanProviderError as exc:
            return Response(
                {"detail": f"OpenAI request failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RegexPlanError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        missing_plan_fields = [
            field for field in ("columns", "regex", "replacement") if field not in plan
        ]
        if missing_plan_fields:
            return Response(
                {"detail": f"The model response was missing: {', '.join(missing_plan_fields)}."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        columns = resolve_column_names(plan.get("columns"), dataframe.columns)
        if not columns:
            return Response(
                {
                    "detail": f"The model selected unknown column(s): {plan.get('columns')}.",
                    "columns": [str(existing_column) for existing_column in dataframe.columns],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        pattern = plan.get("regex", "")
        replacement = plan.get("replacement", "")
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as exc:
            return Response(
                {"detail": f"The model returned an invalid regex: {exc}", "regex": pattern},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        result = apply_replacement(dataframe, dataset_id, columns, compiled_pattern, replacement)
        result.update(
            {
                "natural_language": natural_language,
                "generated_columns": columns,
                "generated_regex": pattern,
                "replacement": replacement,
            }
        )

        return Response(result)


class DownloadDatasetView(APIView):
    def get(self, request, dataset_id):
        dataframe, error_response = get_dataset_or_error(dataset_id)
        if error_response:
            return error_response

        metadata = UploadedDataset.objects.filter(dataset_id=dataset_id).first()
        original_name = metadata.original_name if metadata else f"{dataset_id}.csv"
        return build_download_response(dataframe, original_name)


class DatasetDetailView(APIView):
    def post(self, request, dataset_id):
        deleted = delete_dataset(dataset_id)
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


class DatasetUndoView(APIView):
    def post(self, request, dataset_id):
        dataframe = undo_dataframe(dataset_id)
        if dataframe is None:
            return Response(
                {"detail": "No previous version is available for undo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(build_dataset_response(dataset_id, dataframe))


class DatasetRedoView(APIView):
    def post(self, request, dataset_id):
        dataframe = redo_dataframe(dataset_id)
        if dataframe is None:
            return Response(
                {"detail": "No later version is available for redo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(build_dataset_response(dataset_id, dataframe))

    def delete(self, request, dataset_id):
        deleted = delete_dataset(dataset_id)
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


def delete_dataset(dataset_id):
    datasets = UploadedDataset.objects.filter(dataset_id=dataset_id)
    deleted_count = 0
    for dataset in datasets:
        delete_dataframe(dataset.dataset_id)
        dataset.delete()
        deleted_count += 1
    if deleted_count == 0:
        delete_dataframe(dataset_id)
    return deleted_count > 0


def cleanup_expired_datasets(max_age_hours=24):
    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    expired_datasets = UploadedDataset.objects.filter(uploaded_at__lt=cutoff)
    for dataset in expired_datasets:
        delete_dataframe(dataset.dataset_id)
    expired_datasets.delete()


def get_dataset_or_error(dataset_id):
    try:
        dataframe = load_dataframe(dataset_id)
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        return None, Response(
            {"detail": f"Could not load the stored dataset. Upload the file again. ({exc})"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if dataframe is None:
        return None, Response(
            {"detail": "Dataset not found. Upload the file again and retry."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return dataframe, None


def build_download_response(dataframe, original_name):
    original_path = Path(original_name)
    filename_stem = original_path.stem or "dataset"
    extension = original_path.suffix.lower()

    if extension == ".csv":
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=False)
        response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv; charset=utf-8")
        filename = get_valid_filename(f"processed-{filename_stem}.csv")
    elif extension in {".xls", ".xlsx"}:
        excel_buffer = BytesIO()
        dataframe.to_excel(excel_buffer, index=False, engine="openpyxl")
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = get_valid_filename(f"processed-{filename_stem}.xlsx")
    else:
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=False)
        response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv; charset=utf-8")
        filename = get_valid_filename(f"processed-{filename_stem}.csv")

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def apply_replacement(dataframe, dataset_id, columns, compiled_pattern, replacement):
    push_undo_state(dataset_id)
    match_count = 0
    changed_cells = 0
    for column in columns:
        original_values = dataframe[column].copy()
        dataframe[column] = dataframe[column].apply(
            lambda value: replace_cell(value, compiled_pattern, replacement)
        )
        column_changed_cells = count_changed_cells(original_values, dataframe[column])
        changed_cells += column_changed_cells
        match_count += column_changed_cells

    clean_dataframe = dataframe.where(pd.notnull(dataframe), None)
    save_dataframe(dataset_id, clean_dataframe)
    UploadedDataset.objects.filter(dataset_id=dataset_id).update(
        row_count=len(clean_dataframe.index),
        column_count=len(clean_dataframe.columns),
    )

    response = build_dataset_response(dataset_id, clean_dataframe)
    response.update(
        {
            "match_count": match_count,
            "changed_cells": changed_cells,
        }
    )
    return response


def build_dataset_response(dataset_id, dataframe):
    history_state = history_counts(dataset_id)
    return {
        "dataset_id": dataset_id,
        "columns": [str(existing_column) for existing_column in dataframe.columns],
        "row_count": len(dataframe.index),
        "column_count": len(dataframe.columns),
        "preview_limit": PREVIEW_ROW_LIMIT,
        "can_undo": history_state["can_undo"],
        "can_redo": history_state["can_redo"],
        "preview": dataframe.head(PREVIEW_ROW_LIMIT).to_dict(orient="records"),
    }


def resolve_column_names(candidates, columns):
    if isinstance(candidates, str):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return []

    resolved_columns = []
    for candidate in candidates:
        resolved = resolve_column_name(candidate, columns)
        if not resolved:
            return []
        if resolved not in resolved_columns:
            resolved_columns.append(resolved)

    return resolved_columns


def resolve_column_name(candidate, columns):
    if candidate in columns:
        return candidate

    normalized_candidate = str(candidate).strip().lower()
    for column in columns:
        if str(column).strip().lower() == normalized_candidate:
            return column

    return None


def replace_cell(value, compiled_pattern, replacement):
    if value is None or pd.isna(value):
        return value
    return compiled_pattern.sub(str(replacement), str(value))


def count_changed_cells(original_values, updated_values):
    return sum(
        1
        for original, updated in zip(original_values, updated_values, strict=True)
        if normalize_cell(original) != normalize_cell(updated)
    )


def normalize_cell(value):
    if value is None or pd.isna(value):
        return None
    return str(value)
