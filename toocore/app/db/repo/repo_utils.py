from __future__ import annotations

from datetime import date, datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Date, DateTime, Uuid

ModelT = TypeVar("ModelT")


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _to_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value.strip() == "":
        return None
    return UUID(str(value))


def coerce_model_value(model: Any, key: str, value: Any) -> Any:
    if value is None:
        return None

    table = getattr(model, "__table__", None)
    if table is None:
        return value

    column = table.columns.get(key)
    if column is None:
        return value

    if isinstance(column.type, Date):
        return _to_date(value)
    if isinstance(column.type, DateTime):
        return _to_datetime(value)
    if isinstance(column.type, Uuid):
        return _to_uuid(value)

    return value


def coerce_model_values(model: Any, values: dict[str, Any]) -> dict[str, Any]:
    if not values:
        return values
    return {key: coerce_model_value(model, key, value) for key, value in values.items()}


def model_from_mapping(model: type[ModelT], values: Any) -> ModelT:
    table = getattr(model, "__table__", None)
    if table is None:
        return model(**dict(values))
    data = {column.key: values[column.key] for column in table.columns if column.key in values}
    return model(**data)


def models_from_mappings(model: type[ModelT], rows: list[Any]) -> list[ModelT]:
    return [model_from_mapping(model, row) for row in rows]
