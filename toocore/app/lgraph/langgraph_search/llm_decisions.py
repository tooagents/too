import json
import logging
import re
from datetime import date
from typing import Any

from openai.types.responses.response_format_text_json_schema_config_param import (
    ResponseFormatTextJSONSchemaConfigParam,
)
from openai.types.responses.response_text_config_param import ResponseTextConfigParam

from .llm_client import extract_reasoning_summaries, oai_client

logger = logging.getLogger(__name__)

ROUTER_MODEL = "gpt-5-mini"
TOP_K_MODEL = "gpt-5-mini"
SQL_MODEL = "gpt-5-mini"

ROUTER_FORMAT: ResponseFormatTextJSONSchemaConfigParam = {
    "type": "json_schema",
    "name": "router_decision",
    "description": "Decide whether to use business RAG, SQL, or a general LLM answer.",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "route": {"type": "string", "enum": ["rag", "general", "sql"]},
            "confidence": {"type": "number"},
            "rationale": {"type": "string"},
        },
        "required": ["route", "confidence", "rationale"],
    },
    "strict": True,
}

TOP_K_FORMAT: ResponseFormatTextJSONSchemaConfigParam = {
    "type": "json_schema",
    "name": "top_k_decision",
    "description": "Choose a retrieval top_k value based on query complexity and ambiguity.",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "top_k": {"type": "integer"},
            "rationale": {"type": "string"},
        },
        "required": ["top_k", "rationale"],
    },
    "strict": True,
}

SQL_FORMAT: ResponseFormatTextJSONSchemaConfigParam = {
    "type": "json_schema",
    "name": "sql_generation",
    "description": "Generate a safe single-statement SELECT SQL query.",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sql": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": ["sql", "rationale"],
    },
    "strict": True,
}

SQL_SCHEMA_HINTS = (
    "Tables and columns (PostgreSQL). ALWAYS use schema-qualified names:\n"
    "- too_t4.payroll_history (finalized payroll records): id, ten_id, biz_id, employee_id, full_name, "
    "period_start, period_end, period_key, pay_date, gross, net, total_deduction, bonus, tax, cpp, "
    "ei, regular_hours, overtime_hours, annual_salary_snapshot, hourly_rate_snapshot, status, excluded.\n"
    "- too_t4.payroll_entries (draft payroll entries): id, ten_id, biz_id, employee_id, full_name, "
    "period_start, period_end, period_key, pay_date, gross, net, total_deduction, bonus, tax, cpp, "
    "ei, regular_hours, overtime_hours, annual_salary_snapshot, hourly_rate_snapshot, status, excluded.\n"
    "- too_t4.employees: id, ten_id, biz_id, first_name, last_name, full_name, employment_type, "
    "hourly_rate, annual_salary, start_date, end_date, email, phone.\n"
    "- too_t4.payroll_periods: id, ten_id, biz_id, payroll_schedule_id, start_date, end_date, "
    "pay_date, period_key, period_number, status.\n"
    "- too_t4.payroll_schedules: id, ten_id, biz_id, frequency, payon, effective_from, "
    "effective_to, status.\n"
    "- too_inv.invoice: id, ten_id, biz_id, client_company_name, inv_number, inv_date, inv_due_date, "
    "inv_total, inv_paid_total, inv_balance_due, inv_payment_status.\n"
    "- too_global.zbe (business entity): id, ten_id, biz_id, legal_name, be_number, province, country, employee_count.\n"
    "Notes: Most tables include id, ten_id, biz_id, created_at. Prefer too_t4.payroll_history for finalized reporting.\n"
    # TODO: list the real allowed values for status / inv_payment_status columns here
    # so the model stops guessing them.
)

# ---------------------------------------------------------------------------
# Force-SQL rule: needs BOTH an aggregate intent AND a company-data signal,
# and general/legal wording without a data signal blocks it.
# ---------------------------------------------------------------------------
_AGG_TERMS = [
    "total", "sum", "count", "average", "avg", "min", "max", "median",
    "how many", "how much", "breakdown", "by month", "by employee",
    "by department", "group by", "per month", "per employee", "per department",
]
_DATA_TERMS = [
    "employee", "employees", "payroll", "invoice", "invoices", "gross", "net",
    "tax", "cpp", "ei", "overtime", "bonus", "salary", "wage", "pay date",
    "pay period", "my", "our", "paid", "owed", "balance",
]
_GENERAL_TERMS = [
    "ontario", "entitled", "entitlement", "law", "legal", "rules", "regulation",
    "minimum wage", "what is", "explain", "why",
]


def _word_re(terms: list[str]) -> re.Pattern[str]:
    return re.compile(r"\b(" + "|".join(map(re.escape, terms)) + r")\b", re.I)


_AGG_RE = _word_re(_AGG_TERMS)
_DATA_RE = _word_re(_DATA_TERMS)
_GENERAL_RE = _word_re(_GENERAL_TERMS)


def should_force_sql(query: str) -> tuple[bool, str]:
    q = query or ""
    agg = _AGG_RE.search(q)
    if not agg:
        return False, ""
    if not _DATA_RE.search(q):
        return False, ""
    return True, agg.group(1).lower()


# ---------------------------------------------------------------------------
# Shared LLM call: one place for the call, JSON parse and error handling.
# ---------------------------------------------------------------------------
async def _call_json(
    model: str,
    fmt: ResponseFormatTextJSONSchemaConfigParam,
    messages: list[dict[str, str]],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (payload, reasoning). payload is None on API error or invalid JSON."""
    text_config: ResponseTextConfigParam = {"format": fmt, "verbosity": "low"}
    try:
        response = await oai_client.responses.create(
            model=model,
            input=messages,
            text=text_config,
            reasoning={"summary": "auto"},
        )
    except Exception:
        logger.exception("LLM call failed (model=%s, format=%s)", model, fmt.get("name"))
        return None, []

    reasoning = extract_reasoning_summaries(response)
    try:
        payload = json.loads(response.output_text or "")
    except json.JSONDecodeError:
        return None, reasoning
    if not isinstance(payload, dict):
        return None, reasoning
    return payload, reasoning


async def decide_route(query: str) -> tuple[dict[str, Any], list[str]]:
    system_msg = (
        "You are a router for a payroll and business assistant. "
        "Choose 'sql' when the question can be answered precisely with a single "
        "SELECT query over the business database (lists, counts, totals, exact fields). "
        "Choose 'rag' when the question needs semantic search or narrative answers "
        "grounded in retrieved text chunks. "
        "Choose 'general' for general knowledge, definitions, or advice not tied to "
        "company-specific records (for example legal rules or entitlements). "
        "If unsure, choose 'rag'. "
        "Return JSON that matches the schema."
    )
    payload, reasoning = await _call_json(
        ROUTER_MODEL,
        ROUTER_FORMAT,
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
        ],
    )

    if payload is None:
        payload = {
            "route": "rag",
            "confidence": 0.0,
            "rationale": "Router call failed or returned invalid JSON; defaulted to rag.",
        }
    if payload.get("route") not in {"rag", "general", "sql"}:
        payload["route"] = "rag"
    if not isinstance(payload.get("confidence"), (int, float)):
        payload["confidence"] = 0.0
    if not isinstance(payload.get("rationale"), str):
        payload["rationale"] = "Router rationale missing; defaulted to rag."
    return payload, reasoning


async def decide_top_k(
    query: str,
    default_top_k: int,
    min_k: int = 3,
    max_k: int = 100,
) -> tuple[int, str, list[str]]:
    system_msg = (
        "You choose a retrieval top_k for RAG. "
        "Use higher values for short/ambiguous queries and lower values for specific queries. "
        f"Return an integer between {min_k} and {max_k}."
    )
    payload, reasoning = await _call_json(
        TOP_K_MODEL,
        TOP_K_FORMAT,
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
        ],
    )

    if payload is None:
        return default_top_k, "Top-k call failed; using default.", reasoning

    top_k = payload.get("top_k", default_top_k)
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        top_k = default_top_k
    top_k = max(min_k, min(max_k, top_k))
    rationale = payload.get("rationale") if isinstance(payload.get("rationale"), str) else ""
    return top_k, rationale, reasoning


async def generate_sql(
    query: str,
    previous_sql: str | None = None,
    error: str | None = None,
) -> tuple[str, str, list[str]]:
    system_msg = (
        "You generate a SINGLE SELECT SQL query for the user's request. "
        "Only SELECT (or WITH ... SELECT) is allowed. "
        "No semicolons, no comments, no data modification. "
        "Use only the table names listed in the schema hints, and ALWAYS schema-qualify tables (schema.table). "
        f"Today's date is {date.today().isoformat()}; use it to resolve 'this month', 'last month', 'this year'. "
        "Add LIMIT 100 unless the query is an aggregate that returns one row or a grouped summary. "
        "Do not invent values for status columns; only filter on status if the user asks for it. "
        "Return JSON that matches the schema."
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_msg},
        {"role": "system", "content": SQL_SCHEMA_HINTS},
        {"role": "user", "content": query},
    ]
    if previous_sql and error:
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Your previous SQL was:\n{previous_sql}\n"
                    f"It failed with: {error}\n"
                    "Return a corrected single SELECT query."
                ),
            }
        )

    payload, reasoning = await _call_json(SQL_MODEL, SQL_FORMAT, messages)
    if payload is None:
        return "", "SQL generator call failed or returned invalid JSON.", reasoning

    sql = payload.get("sql") if isinstance(payload.get("sql"), str) else ""
    rationale = payload.get("rationale") if isinstance(payload.get("rationale"), str) else ""
    return sql, rationale, reasoning