from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.inv.i_payment_method import PaymentMethodDB
from app.db.repo.repo_utils import coerce_model_values, model_from_mapping, models_from_mappings

_log = logging.getLogger("app.http")


async def _read_rls_context(db: AsyncConnection) -> dict:
    result = await db.execute(
        text(
            "select "
            "current_user::text as current_user, "
            "session_user::text as session_user, "
            "current_setting('role', true)::text as active_role, "
            "current_setting('request.jwt.claims', true)::jsonb ->> 'sub' as jwt_sub, "
            "current_setting('request.jwt.claims', true)::jsonb ->> 'sba_ten_id' as jwt_ten_id"
        )
    )
    row = result.mappings().one()
    return dict(row)


async def _read_payment_method_snapshot(
    db: AsyncConnection, method_id: UUID
) -> Optional[dict]:
    result = await db.execute(
        text(
            "select "
            "id::text as id, "
            "ten_id::text as ten_id, "
            "created_by::text as created_by, "
            "pm_name::text as pm_name "
            "from too_inv.ipayment_method "
            "where id = :method_id"
        ),
        {"method_id": str(method_id)},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_payment_methods(db: AsyncConnection, actor_id: UUID) -> List[PaymentMethodDB]:
    ctx = await _read_rls_context(db)
    _log.info("pm.list start actor_id=%s rls_ctx=%s", actor_id, ctx)
    table = PaymentMethodDB.__table__
    result = await db.execute(
        select(table)
        .where(table.c.created_by == actor_id, table.c.is_deleted.isnot(True))
        .order_by(table.c.created_at.desc())
    )
    rows = models_from_mappings(PaymentMethodDB, list(result.mappings().all()))
    _log.info("pm.list done actor_id=%s count=%s", actor_id, len(rows))
    return rows


async def get_payment_method_by_id(
    db: AsyncConnection, method_id: UUID, actor_id: UUID
) -> Optional[PaymentMethodDB]:
    ctx = await _read_rls_context(db)
    _log.info(
        "pm.get_by_id start method_id=%s actor_id=%s rls_ctx=%s",
        method_id,
        actor_id,
        ctx,
    )
    table = PaymentMethodDB.__table__
    result = await db.execute(
        select(table).where(table.c.id == method_id, table.c.created_by == actor_id)
    )
    raw = result.mappings().one_or_none()
    row = model_from_mapping(PaymentMethodDB, raw) if raw else None
    _log.info(
        "pm.get_by_id done method_id=%s actor_id=%s found=%s found_ten_id=%s found_created_by=%s",
        method_id,
        actor_id,
        bool(row),
        str(row.ten_id) if row else None,
        str(row.created_by) if row else None,
    )
    return row


async def create_payment_method(db: AsyncConnection, payload: dict) -> PaymentMethodDB:
    table = PaymentMethodDB.__table__
    # The ipayment_method.id column has no DB-side default, so generate one here
    # rather than relying on the model's server_default (not present on the table).
    values = coerce_model_values(PaymentMethodDB, payload)
    values.setdefault("id", uuid4())
    result = await db.execute(
        insert(table)
        .values(**values)
        .returning(*table.c)
    )
    return model_from_mapping(PaymentMethodDB, result.mappings().one())


async def update_payment_method_fields(
    db: AsyncConnection,
    method: PaymentMethodDB,
    updates: dict,
    actor_id: UUID,
    expected_ten_id: UUID | str,
) -> PaymentMethodDB:
    if not updates:
        return method
    table = PaymentMethodDB.__table__
    result = await db.execute(
        update(table)
        .where(table.c.id == method.id)
        .values(**coerce_model_values(PaymentMethodDB, updates))
        .returning(*table.c)
    )
    return model_from_mapping(PaymentMethodDB, result.mappings().one())
