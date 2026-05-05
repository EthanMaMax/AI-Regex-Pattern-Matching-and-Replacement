import json
import os

from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


REGEX_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "columns": {
            "type": "array",
            "description": (
                "Target column names selected from the provided columns. "
                "If the user explicitly names one or more columns, include only those columns. "
                "If the user says everywhere, all columns, or does not specify any columns, "
                "include every provided column."
            ),
            "items": {
                "type": "string",
            },
        },
        "regex": {
            "type": "string",
            "description": "A Python re-compatible regex pattern.",
        },
        "replacement": {
            "type": "string",
            "description": "The replacement value requested by the user.",
        },
    },
    "required": ["columns", "regex", "replacement"],
}


def generate_regex_plan(natural_language, columns):
    load_dotenv(settings.BASE_DIR / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise MissingOpenAIKeyError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    columns_text = ", ".join(str(column) for column in columns)

    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You convert user requests into regex replacement plans for tabular data. "
                "Choose one or more target columns from the provided column list. "
                "When the user mentions multiple columns, include all of them. "
                "When the user says everywhere, all columns, or does not explicitly specify "
                "a target column, include every provided column. Do not infer a single column "
                "from the meaning of the search term when no column is specified. "
                "Return a Python re-compatible regex. "
                "Extract the replacement value from the user request. "
                "If the user does not specify a replacement value, use an empty string."
            ),
            input=(
                f"Available columns: {columns_text}\n"
                f"User request: {natural_language}"
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "regex_replacement_plan",
                    "schema": REGEX_PLAN_SCHEMA,
                    "strict": True,
                }
            },
            temperature=0,
        )
    except OpenAIError as exc:
        raise RegexPlanProviderError(str(exc)) from exc

    try:
        return json.loads(response.output_text)
    except (AttributeError, json.JSONDecodeError) as exc:
        raise RegexPlanError("The model did not return a valid regex plan.") from exc


class MissingOpenAIKeyError(Exception):
    pass


class RegexPlanError(Exception):
    pass


class RegexPlanProviderError(Exception):
    pass
