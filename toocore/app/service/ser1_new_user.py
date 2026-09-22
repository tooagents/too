from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.supabase_meta import updateid_ten_cli
from app.db.seed.new_user_defaults import NEW_USER_DEFAULTS, default_payroll_schedule_templates
from app.db.models.t4.m_payroll_schedule import PayrollScheduleDB
from app.db.models.too.z_be import ZBizEntityDB
from app.db.models.too.z_client import ZClientDB
from app.db.models.too.z_user import ZUserDB
from app.db.models.too.z_user_client import ZUserClientDB
from app.schemas.sch_ai import JWType
from app.service.ser_seed import apply_seed_defaults

_log = logging.getLogger(__name__)


async def _ensure_default_payroll_schedules(
    db: AsyncConnection,
    *,
    ten_id: UUID|None,
    cli_id: UUID|None,
    usr_id: UUID|None,
    created_by: UUID|None,
) -> None:
    _log.info("---------- provision payroll schedules start cli_id=%s", cli_id)
    created = 0
    skipped = 0
    for template in default_payroll_schedule_templates():
        existing_id = await db.scalar(
            select(PayrollScheduleDB.id).where(
                PayrollScheduleDB.cli_id == cli_id,
                PayrollScheduleDB.frequency == template["frequency"],
            )
        )
        if existing_id:
            skipped += 1
            _log.info(
                "---------- provision payroll schedule skip frequency=%s cli_id=%s",
                template.get("frequency"),
                cli_id,
            )
            continue
        await db.execute(
            insert(PayrollScheduleDB).values(
                ten_id=ten_id,
                biz_id=cli_id,
                cli_id=cli_id,
                usr_id=usr_id,
                created_by=created_by,
                **template,
            )
        )
        created += 1
        _log.info(
            "---------- provision payroll schedule inserted frequency=%s cli_id=%s",
            template.get("frequency"),
            cli_id,
        )
    _log.info(
        "---------- provision payroll schedules done cli_id=%s created=%s skipped=%s",
        cli_id,
        created,
        skipped,
    )



async def provision_new_user_with_seed(zjwt: JWType, db: AsyncConnection) -> None:
    zuid = zjwt.zuid    
    if not zuid:
        raise ValueError("Invalid JWT: missing user id")
    _log.info("---------- provision start zuid=%s email=%s", zuid, zjwt.zemail)

    user_metadata = zjwt.user_metadata or {}
    zemail = zjwt.zemail or NEW_USER_DEFAULTS["email"]
    sbu_user_type = user_metadata.get("sbu_user_type") or "T4USER"

    display_name = (
        user_metadata.get("sbu_user_name")
        or user_metadata.get("sbu_name")
        or user_metadata.get("full_name")
        or user_metadata.get("name")
        or zemail
        or NEW_USER_DEFAULTS["name"]
    )
    avatar = (
        user_metadata.get("sbu_user_avatar")
        or user_metadata.get("sbu_avatar")
        or user_metadata.get("avatar_url")
        or user_metadata.get("picture")
        or NEW_USER_DEFAULTS["avatar"]
    )
    business_name = user_metadata.get("sbu_client_name") or "My Business"

    base_ids = {
        "id": zuid,
        "ten_id": zuid,
        "biz_id": zuid,
        "usr_id": zuid,
        "cli_id": zuid,
        "created_by": zuid,
    }

    _log.info("---------- provision check existing user_client zuid=%s", zuid)
    existing_user_client_id = await db.scalar(
        select(ZUserClientDB.id).where(ZUserClientDB.id == zuid)
    )
    if existing_user_client_id:
        _log.info("---------- provision existing user_client found zuid=%s", zuid)
        _log.info("---------- provision supabase metadata update start zuid=%s", zuid)
        await updateid_ten_cli(zuid)
        _log.info("---------- provision supabase metadata update done zuid=%s", zuid)
        return

    zuser_payload = {
        **base_ids,
        "email": zemail,
        "display_name": display_name,
        "name": display_name,
        "usr_type": sbu_user_type,
        "full_name": display_name,
        "first_name": display_name,
        "last_name": display_name,
        "avatar": avatar,
        "phone": NEW_USER_DEFAULTS["phone"],
        "position": NEW_USER_DEFAULTS["position"],
        "facebook": NEW_USER_DEFAULTS["facebook"],
        "twitter": NEW_USER_DEFAULTS["twitter"],
        "github": NEW_USER_DEFAULTS["github"],
        "reddit": NEW_USER_DEFAULTS["reddit"],
        "country": NEW_USER_DEFAULTS["country"],
        "state": NEW_USER_DEFAULTS["state"],
        "pin": NEW_USER_DEFAULTS["pin"],
        "zip": NEW_USER_DEFAULTS["zip"],
        "tax_no": NEW_USER_DEFAULTS["taxNo"],
    }

    zbe_payload = {
        **base_ids,
        "be_name": business_name,
        "be_type": "ME",
        "be_email": zemail,
        "be_phone": NEW_USER_DEFAULTS["phone"],
        "be_contact": display_name,
        "be_logo": "https://raw.githubusercontent.com/ainvoaice/ainvoAIce/refs/heads/main/entrepreneurs.jpg",
    }

    zclient_payload = {
        **base_ids,
        "client_company_name": zbe_payload.get("be_name"),
        "client_contact_name": zbe_payload.get("be_contact"),
        "client_contact_title": zbe_payload.get("be_contact_title"),
        "client_address": zbe_payload.get("be_address"),
        "client_email": zbe_payload.get("be_email"),
        "client_mainphone": zbe_payload.get("be_phone"),
        "client_website": zbe_payload.get("be_website"),
        "client_tax_id": zbe_payload.get("be_tax_id"),
        "client_payment_term": zbe_payload.get("be_payment_term"),
        "client_currency": zbe_payload.get("be_currency"),
        "client_template_id": zbe_payload.get("be_inv_template_id"),
        "client_terms_conditions": zbe_payload.get("be_description"),
        "client_note": zbe_payload.get("be_note"),
    }

    z_user_client_payload = {**base_ids}

    try:
        _log.info("---------- provision z_user upsert start zuid=%s", zuid)
        await db.execute(
            insert(ZUserDB)
            .values(**zuser_payload)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"usr_type": sbu_user_type},
            )
        )
        _log.info("---------- provision z_user upsert done zuid=%s", zuid)

        _log.info("---------- provision z_biz_entity insert start zuid=%s", zuid)
        await db.execute(insert(ZBizEntityDB).values(**zbe_payload).on_conflict_do_nothing(index_elements=["id"]))
        _log.info("---------- provision z_biz_entity insert done zuid=%s", zuid)

        _log.info("---------- provision z_client insert start zuid=%s", zuid)
        await db.execute(insert(ZClientDB).values(**zclient_payload).on_conflict_do_nothing(index_elements=["id"]))
        _log.info("---------- provision z_client insert done zuid=%s", zuid)

        _log.info("---------- provision z_user_client insert start zuid=%s", zuid)
        await db.execute(insert(ZUserClientDB).values(**z_user_client_payload).on_conflict_do_nothing(index_elements=["id"]))
        _log.info("---------- provision z_user_client insert done zuid=%s", zuid)

        await _ensure_default_payroll_schedules(
            db,
            ten_id=zuid,
            cli_id=zuid,
            usr_id=zuid,
            created_by=zuid,
        )

        _log.info("---------- provision seed defaults start zuid=%s", zuid)
        seed_summary = await apply_seed_defaults(zjwt=zjwt, db=db, reset=False)
        _log.info("---------- provision seed defaults done zuid=%s summary=%s", zuid, seed_summary)
    except Exception:
        _log.exception("---------- provision failed zuid=%s", zuid)
        raise
    _log.info("---------- provision supabase metadata update start zuid=%s", zuid)
    await updateid_ten_cli(zuid)
    _log.info("---------- provision done zuid=%s", zuid)
