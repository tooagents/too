from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.models.acc.ac_coa import COADB
from app.db.models.acc.ac_ledger import JournalEntryLine
from app.schemas.sch_acc_coa import (
    COACreate,
    COARoot,
    COAOut,
    COATreeOut,
    COAUpdate,
    NormalBalanceType,
)
from app.schemas.sch_ai import JWType
from app.service.acc.coa_templates import (
    generic_startup_template,
    get_coa_template,
    get_coa_template_name,
    list_coa_templates,
)

_ROOT_COA_CODES: dict[str, COARoot] = {
    "1000": "Asset",
    "2000": "Liability",
    "3000": "Equity",
    "4000": "Revenue",
    "5000": "Expense",
}

_NORMAL_BALANCE_VALUES = ("Debit", "Credit")
COA_TABLE = COADB.__table__
JE_LINE_TABLE = JournalEntryLine.__table__

def _normal_balance(value: str | None) -> NormalBalanceType | None:
    if value is None:
        return None
    if value not in _NORMAL_BALANCE_VALUES:
        raise ValueError(f"Invalid normal balance: {value}")
    return value


def _to_account_out(row: Mapping[str, Any]) -> COAOut:
    return COAOut(
        id=row["id"],
        parent_id=row["parent_id"],
        coa_code=row["coa_code"],
        coa_name=row["coa_name"],
        coa_status=row["coa_status"],
        coa_level=row["coa_level"],
        normal_balance=_normal_balance(row["normal_balance"]),
        is_posting=row["is_posting"],
        is_readonly=row["is_readonly"],
        is_deleted=row["is_deleted"],
    )


def _to_tree_out(row: Mapping[str, Any]) -> COATreeOut:
    return COATreeOut(**_to_account_out(row).model_dump(), children=[])


def _is_reserved_root_payload(payload: COACreate) -> bool:
    return payload.coa_code in _ROOT_COA_CODES and payload.parent_id is None and payload.is_posting is False


def _ensure_coa_mutable(account: Mapping[str, Any]) -> None:
    if account["is_readonly"] is True:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Readonly COA account cannot be modified",
        )


def _normalize_create(payload: COACreate) -> dict:
    data = payload.model_dump()
    data["normal_balance"] = _normal_balance(data.get("normal_balance"))
    return data


def _normalize_updates(payload: COAUpdate) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if "normal_balance" in updates and updates["normal_balance"] is not None:
        updates["normal_balance"] = _normal_balance(updates["normal_balance"])
    return updates


async def _get_coa_or_404(conn: AsyncConnection, coa_id: UUID) -> Mapping[str, Any]:
    row = (
        await conn.execute(
            select(COA_TABLE)
            .where(COA_TABLE.c.id == coa_id)
        )
    ).mappings().one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="COA account not found",
        )
    return row


async def _get_parent_or_404(conn: AsyncConnection, parent_id: UUID | None) -> Mapping[str, Any] | None:
    if parent_id is None:
        return None
    parent = await _get_coa_or_404(conn, parent_id)
    if parent["is_posting"] is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Posting COA account cannot be used as a parent",
        )
    return parent


async def _ensure_not_descendant(conn: AsyncConnection, *, account_id: UUID, new_parent_id: UUID | None) -> None:
    if new_parent_id is None:
        return
    if new_parent_id == account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="COA account cannot be its own parent")

    rows = list(
        (
            await conn.execute(
                select(COA_TABLE.c.id, COA_TABLE.c.parent_id)
                .where(COA_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    parent_by_id = {row["id"]: row["parent_id"] for row in rows}
    current = new_parent_id
    seen: set[UUID] = set()
    while current is not None and current not in seen:
        if current == account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="COA parent would create a cycle")
        seen.add(current)
        current = parent_by_id.get(current)


def _derived_coa_level(parent: Mapping[str, Any] | None) -> int:
    return int(parent["coa_level"] or 1) + 1 if parent else 1


async def _refresh_descendant_levels(conn: AsyncConnection, account: Mapping[str, Any]) -> None:
    rows = list(
        (
            await conn.execute(
                select(COA_TABLE)
                .where(COA_TABLE.c.is_deleted.is_not(True))
            )
        ).mappings().all()
    )
    children_by_parent: dict[UUID, list[Mapping[str, Any]]] = {}
    for row in rows:
        if row["parent_id"]:
            children_by_parent.setdefault(row["parent_id"], []).append(row)

    async def apply(parent: Mapping[str, Any]) -> None:
        parent_level = int(parent["coa_level"] or 1)
        for child in children_by_parent.get(parent["id"], []):
            child_level = parent_level + 1
            await conn.execute(
                update(COA_TABLE)
                .where(COA_TABLE.c.id == child["id"])
                .values(coa_level=child_level)
            )
            await apply({**child, "coa_level": child_level})

    await apply(account)


async def list_coa(conn: AsyncConnection, active_only: bool = True) -> list[COAOut]:
    stmt = select(COA_TABLE).order_by(COA_TABLE.c.coa_code.asc())
    if active_only:
        stmt = stmt.where(COA_TABLE.c.is_deleted.is_not(True))

    rows = (await conn.execute(stmt)).mappings().all()
    return [_to_account_out(row) for row in rows]


async def list_coa_tree(conn: AsyncConnection, active_only: bool = False) -> list[COATreeOut]:
    stmt = select(COA_TABLE).order_by(COA_TABLE.c.coa_level.asc(), COA_TABLE.c.coa_code.asc())
    if active_only:
        stmt = stmt.where(COA_TABLE.c.is_deleted.is_not(True))

    rows = (await conn.execute(stmt)).mappings().all()
    nodes_by_id = {row["id"]: _to_tree_out(row) for row in rows}
    roots: list[COATreeOut] = []

    for row in rows:
        node = nodes_by_id[row["id"]]
        parent = nodes_by_id.get(row["parent_id"]) if row["parent_id"] else None
        if parent is None:
            roots.append(node)
            continue
        parent.children.append(node)

    return roots


async def create_coa_account(conn: AsyncConnection,zjwt: JWType,payload: COACreate,) -> COAOut:
    if payload.coa_code in _ROOT_COA_CODES and not _is_reserved_root_payload(payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reserved COA root code",
        )

    exists = (
        await conn.execute(
            select(COA_TABLE.c.id)
            .where(COA_TABLE.c.coa_code == payload.coa_code)
            .where(COA_TABLE.c.is_deleted.is_not(True))
        )
    ).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="COA code already exists",
        )

    parent = await _get_parent_or_404(conn, payload.parent_id)
    data = _normalize_create(payload)
    data["coa_level"] = _derived_coa_level(parent)
    if payload.coa_code in _ROOT_COA_CODES:
        data["coa_name"] = _ROOT_COA_CODES[payload.coa_code]
        data["is_readonly"] = True

    data.update(
        ten_id=zjwt.ztid,
        biz_id=zjwt.zbid,
        usr_id=zjwt.zuid,
        created_by=zjwt.zuid,
    )

    try:
        account = (
            await conn.execute(
                insert(COA_TABLE)
                .values(**data)
                .returning(*COA_TABLE.c)
            )
        ).mappings().one()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create COA account",
        ) from exc

    return _to_account_out(account)


async def get_coa_account(conn: AsyncConnection, coa_id: UUID) -> COAOut:
    return _to_account_out(await _get_coa_or_404(conn, coa_id))


def list_coa_template_summaries() -> dict[str, object]:
    return {"templates": list_coa_templates()}


def get_generic_coa_template() -> dict[str, object]:
    return {
        "template": "minimal-ca",
        "name": "Minimal Canada",
        "seed_required": False,
        "accounts": generic_startup_template(),
    }


def get_coa_template_response(template_key: str) -> dict[str, object]:
    template = get_coa_template(template_key)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="COA template not found",
        )
    return {
        "template": template_key,
        "name": get_coa_template_name(template_key),
        "seed_required": False,
        "accounts": template,
    }


async def apply_generic_coa_template(conn: AsyncConnection, zjwt: JWType) -> dict[str, object]:
    return await apply_coa_template(conn=conn, zjwt=zjwt, template_key="minimal-ca")


async def apply_coa_template(
    conn: AsyncConnection,
    zjwt: JWType,
    template_key: str,
) -> dict[str, object]:
    template = get_coa_template(template_key)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="COA template not found",
        )

    created = 0
    existing = 0
    for item in template:
        found = (
            await conn.execute(
                select(COA_TABLE.c.id).where(COA_TABLE.c.coa_code == item["coa_code"])
            )
        ).first()
        if found:
            existing += 1
            continue

        try:
            await conn.execute(
                insert(COA_TABLE).values(
                    ten_id=zjwt.ztid,
                    biz_id=zjwt.zbid,
                    usr_id=zjwt.zuid,
                    created_by=zjwt.zuid,
                    coa_code=item["coa_code"],
                    coa_name=item["coa_name"],
                    parent_id=item["parent_id"],
                    coa_status=item["coa_status"],
                    coa_level=item["coa_level"],
                    normal_balance=item["normal_balance"],
                    is_posting=item["is_posting"],
                    is_readonly=item["is_readonly"],
                )
            )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to apply COA template",
            ) from exc
        created += 1

    return {"template": template_key, "created": created, "existing": existing}


async def update_coa_account(
    conn: AsyncConnection,
    coa_id: UUID,
    payload: COAUpdate,
) -> COAOut:
    account = await _get_coa_or_404(conn, coa_id)
    _ensure_coa_mutable(account)
    updates = _normalize_updates(payload)
    if not updates:
        return _to_account_out(account)

    new_code = updates.get("coa_code")
    if new_code and new_code != account["coa_code"]:
        exists = (
            await conn.execute(
                select(COA_TABLE.c.id)
                .where(COA_TABLE.c.coa_code == new_code)
                .where(COA_TABLE.c.id != coa_id)
            )
        ).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="COA code already exists",
            )

    if "parent_id" in updates:
        await _ensure_not_descendant(conn, account_id=coa_id, new_parent_id=updates["parent_id"])
        parent = await _get_parent_or_404(conn, updates["parent_id"])
        updates["coa_level"] = _derived_coa_level(parent)

    if updates.get("is_posting") is True:
        child = (
            await conn.execute(
                select(COA_TABLE.c.id)
                .where(COA_TABLE.c.parent_id == coa_id)
                .where(COA_TABLE.c.is_deleted.is_not(True))
            )
        ).first()
        if child:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="COA account with child accounts cannot be posting",
            )

    if updates.get("coa_code") in _ROOT_COA_CODES and account["parent_id"] is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reserved COA root code",
        )

    try:
        account = (
            await conn.execute(
                update(COA_TABLE)
                .where(COA_TABLE.c.id == coa_id)
                .values(**updates)
                .returning(*COA_TABLE.c)
            )
        ).mappings().one()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update COA account",
        ) from exc

    if "parent_id" in updates:
        await _refresh_descendant_levels(conn, account)
        account = await _get_coa_or_404(conn, coa_id)

    return _to_account_out(account)


async def delete_coa_account(conn: AsyncConnection, coa_id: UUID) -> None:
    account = await _get_coa_or_404(conn, coa_id)
    _ensure_coa_mutable(account)
    child = (
        await conn.execute(
            select(COA_TABLE.c.id)
            .where(COA_TABLE.c.parent_id == coa_id)
            .where(COA_TABLE.c.is_deleted.is_not(True))
        )
    ).first()
    if child:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="COA account has child accounts",
        )
    line = (
        await conn.execute(
            select(JE_LINE_TABLE.c.id)
            .where(JE_LINE_TABLE.c.account_id == coa_id)
            .where(JE_LINE_TABLE.c.is_deleted.is_not(True))
        )
    ).first()
    if line:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="COA account is used by journal entries",
        )
    await conn.execute(
        update(COA_TABLE)
        .where(COA_TABLE.c.id == coa_id)
        .values(coa_status="Archived", is_deleted=True)
    )
