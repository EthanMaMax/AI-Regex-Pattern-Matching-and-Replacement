import json
from pathlib import Path

import pandas as pd
from django.conf import settings


DATASET_STORAGE_DIR = Path(settings.BASE_DIR) / "data" / "datasets"
HISTORY_STORAGE_DIR = Path(settings.BASE_DIR) / "data" / "history"


def save_dataframe(dataset_id, dataframe):
    DATASET_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "columns": [str(column) for column in dataframe.columns],
        "records": dataframe.to_dict(orient="records"),
    }
    path = dataset_path(dataset_id)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def load_dataframe(dataset_id):
    path = dataset_path(dataset_id)
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(payload["records"], columns=payload["columns"])


def delete_dataframe(dataset_id):
    dataset_path(dataset_id).unlink(missing_ok=True)
    history_path(dataset_id).unlink(missing_ok=True)


def load_payload(dataset_id):
    path = dataset_path(dataset_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_payload(dataset_id, payload):
    DATASET_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path(dataset_id).write_text(json.dumps(payload), encoding="utf-8")


def load_history(dataset_id):
    path = history_path(dataset_id)
    if not path.exists():
        return {"undo": [], "redo": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_history(dataset_id, history):
    HISTORY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    history_path(dataset_id).write_text(json.dumps(history), encoding="utf-8")


def push_undo_state(dataset_id):
    payload = load_payload(dataset_id)
    if payload is None:
        return
    history = load_history(dataset_id)
    history["undo"].append(payload)
    history["redo"] = []
    save_history(dataset_id, history)


def undo_dataframe(dataset_id):
    current_payload = load_payload(dataset_id)
    history = load_history(dataset_id)
    if current_payload is None or not history["undo"]:
        return None

    previous_payload = history["undo"].pop()
    history["redo"].append(current_payload)
    save_payload(dataset_id, previous_payload)
    save_history(dataset_id, history)
    return pd.DataFrame(previous_payload["records"], columns=previous_payload["columns"])


def redo_dataframe(dataset_id):
    current_payload = load_payload(dataset_id)
    history = load_history(dataset_id)
    if current_payload is None or not history["redo"]:
        return None

    next_payload = history["redo"].pop()
    history["undo"].append(current_payload)
    save_payload(dataset_id, next_payload)
    save_history(dataset_id, history)
    return pd.DataFrame(next_payload["records"], columns=next_payload["columns"])


def history_counts(dataset_id):
    history = load_history(dataset_id)
    return {
        "can_undo": len(history["undo"]) > 0,
        "can_redo": len(history["redo"]) > 0,
    }


def dataset_path(dataset_id):
    return DATASET_STORAGE_DIR / f"{dataset_id}.json"


def history_path(dataset_id):
    return HISTORY_STORAGE_DIR / f"{dataset_id}.json"
