import inspect
import json

from app.agent.brain import (
    SQL_MODEL,
    TOP_K_MODEL,
    decide_route,
    decide_top_k,
    generate_sql,
    should_force_sql,
)
from app.agent.tools import (
    GENERAL_MODEL,
    execute_sql,
    general_answer,
    run_rag_rerank,
    validate_sql_select,
)
from app.lgraph.langgraph_search.state import StateSearch

ROUTES = ("rag", "sql", "general")
MAX_SQL_ATTEMPTS = 2
MIN_RAG_CONFIDENCE = 0.5  # tune to your real confidence range


async def _emit_status(
    state: StateSearch,
    status: str,
    meta: dict | None = None,
) -> None:
    cb = state.get("status_cb")
    if not cb:
        return
    try:
        result = cb(status, meta or {})
        if inspect.isawaitable(result):
            await result
    except Exception:
        return


def node_init_state(state: StateSearch) -> StateSearch:
    return state


# ---------------------------------------------------------------------------
# Router node
# ---------------------------------------------------------------------------
async def node_orchestration(state: StateSearch) -> StateSearch:
    query = state.get("query") or ""
    tried = list(state.get("tried_routes") or [])
    attempts = state.get("attempts", 0)
    forced_sql = bool(state.get("forced_sql"))

    await _emit_status(
        state,
        "routing_start",
        {"query": query, "attempt": attempts + 1, "tried": tried},
    )

    force_sql, force_kw = should_force_sql(query)
    if force_sql and "sql" not in tried:
        forced_sql = True
        decision = {
            "route": "sql",
            "confidence": 1.0,
            "rationale": f"Keyword '{force_kw}' with company-data context implies SQL.",
        }
        route_reasoning = [decision["rationale"]]
    else:
        decision, route_reasoning = await decide_route(query)
        route_reasoning = list(route_reasoning or [])
        route = decision.get("route", "rag")

        # Never repeat a route that already ran; never fall to 'general' for a forced-SQL question
        blocked = set(tried)
        if forced_sql:
            blocked.add("general")
        if route in blocked:
            untried = [r for r in ROUTES if r not in blocked]
            switched = untried[0] if untried else "rag"
            note = f"Route '{route}' not allowed or already tried; switching to '{switched}'."
            decision = {**decision, "route": switched, "rationale": note}
            route_reasoning.append(note)

    route = decision.get("route", "rag")
    await _emit_status(
        state,
        "routing_done",
        {
            "route": route,
            "confidence": decision.get("confidence"),
            "rationale": decision.get("rationale"),
        },
    )
    return {
        **state,
        "decision": decision,
        "route_reasoning": route_reasoning,
        "route": route,
        "attempts": attempts + 1,
        "tried_routes": tried + [route],
        "forced_sql": forced_sql,
    }


# ---------------------------------------------------------------------------
# RAG node
# ---------------------------------------------------------------------------
def _rag_is_weak(rag_response) -> bool:
    if not isinstance(rag_response, dict):
        return True
    if not rag_response.get("evidence"):
        return True
    conf = rag_response.get("confidence")
    return isinstance(conf, (int, float)) and conf < MIN_RAG_CONFIDENCE


async def node_rag(state: StateSearch) -> StateSearch:
    query = state.get("query") or ""
    top_k = state.get("top_k")
    zjwt = state.get("zjwt")
    db = state.get("db")
    await _emit_status(state, "rag_start", {"query": query, "top_k": top_k})

    decided_top_k, top_k_rationale, top_k_reasoning = await decide_top_k(
        query,
        default_top_k=top_k,
    )
    await _emit_status(
        state,
        "rag_top_k",
        {"top_k": decided_top_k, "rationale": top_k_rationale},
    )
    rag_response = await run_rag_rerank(
        query,
        decided_top_k,
        zjwt,
        db,
        status_cb=state.get("status_cb"),
    )
    if isinstance(rag_response, dict):
        rag_response["route"] = "rag"
        if top_k_reasoning:
            rag_response["model_reasoning_summary"] = (
                list(top_k_reasoning) + list(rag_response.get("model_reasoning_summary") or [])
            )
        rag_response["top_k"] = decided_top_k
        rag_response["model"] = TOP_K_MODEL
    await _emit_status(
        state,
        "rag_done",
        {"top_k": decided_top_k, "model": TOP_K_MODEL},
    )

    return {
        **state,
        "rag_response": rag_response,
        "response": rag_response,
        "answer_ok": not _rag_is_weak(rag_response),
    }


# ---------------------------------------------------------------------------
# SQL node
# ---------------------------------------------------------------------------
def _rows_are_empty(rows) -> bool:
    """No rows, or one row whose values are all NULL (for example SUM over nothing)."""
    if not rows:
        return True
    if len(rows) == 1 and isinstance(rows[0], dict):
        return all(v is None for v in rows[0].values())
    return False


def _cannot_compute_response(state: StateSearch, sql_text: str, reason: str) -> dict:
    """Explicit failure for accounting questions, instead of an unverified answer."""
    return {
        "query": state.get("query") or "",
        "route": "sql",
        "sql": sql_text,
        "top_k": state.get("top_k"),
        "model": SQL_MODEL,
        "rerank_model": "router-sql",
        "answer": "I couldn't compute this from your records.",
        "confidence": 0.0,
        "reasoning_summary": ["SQL could not be executed successfully."],
        "citations": [],
        "limitations": reason,
        "model_reasoning_summary": [reason],
        "evidence": [],
    }


async def _rag_fallback(state: StateSearch, sql_text: str, note: str) -> StateSearch:
    rag_response = await run_rag_rerank(
        state.get("query") or "",
        state.get("top_k"),
        state.get("zjwt"),
        state.get("db"),
        status_cb=state.get("status_cb"),
    )
    if isinstance(rag_response, dict):
        rag_response["route"] = "sql"
        rag_response["sql"] = sql_text
        rag_response["model_reasoning_summary"] = (
            [note] + list(rag_response.get("model_reasoning_summary") or [])
        )
        rag_response["limitations"] = (
            "Not computed from the database. " + str(rag_response.get("limitations") or "")
        ).strip()
    return {**state, "sql_text": sql_text, "response": rag_response}


async def node_sql(state: StateSearch) -> StateSearch:
    query = state.get("query") or ""
    db = state.get("db")
    top_k = state.get("top_k")
    forced_sql = bool(state.get("forced_sql"))
    # RAG fallback is only allowed for non-forced questions and only if RAG has not already run
    allow_rag_fallback = not forced_sql and "rag" not in (state.get("tried_routes") or [])

    await _emit_status(state, "sql_start", {"query": query})

    sql_text, sql_rationale, sql_reasoning = "", None, []
    last_error: str | None = None
    rows = None

    for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
        sql_text, sql_rationale, sql_reasoning = await generate_sql(
            query,
            previous_sql=sql_text if last_error else None,
            error=last_error,
        )
        await _emit_status(state, "sql_generated", {"sql": sql_text, "attempt": attempt})

        ok, reason = validate_sql_select(sql_text)
        if not ok:
            last_error = f"Guardrail rejected query: {reason}"
            await _emit_status(
                state,
                "sql_guardrail_rejected",
                {"reason": reason, "sql": sql_text, "attempt": attempt},
            )
            continue

        try:
            await _emit_status(state, "sql_execute", {"sql": sql_text, "attempt": attempt})
            rows = await execute_sql(db, sql_text)
            break
        except Exception as exc:
            last_error = str(exc)
            await _emit_status(
                state,
                "sql_execute_failed",
                {"error": last_error, "sql": sql_text, "attempt": attempt},
            )
    else:
        # every attempt failed
        reason = f"SQL failed after {MAX_SQL_ATTEMPTS} attempts: {last_error}"
        if allow_rag_fallback:
            return await _rag_fallback(state, sql_text, reason + " (fell back to RAG)")
        return {
            **state,
            "sql_text": sql_text,
            "response": _cannot_compute_response(state, sql_text, reason),
        }

    empty = _rows_are_empty(rows)
    if empty and allow_rag_fallback:
        # Not a forced-SQL question and the query found nothing useful: try RAG
        return await _rag_fallback(
            state, sql_text, "SQL returned no usable result; fell back to RAG."
        )

    answer_text = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
    combined_reasoning = list(sql_reasoning or [])
    if sql_rationale:
        combined_reasoning.insert(0, sql_rationale)

    response = {
        "query": query,
        "route": "sql",
        "sql": sql_text,
        "top_k": top_k,
        "model": SQL_MODEL,
        "rerank_model": "router-sql",
        "answer": answer_text,
        "confidence": 1.0,
        "reasoning_summary": ["SQL executed successfully."],
        "citations": [],
        "limitations": "No matching records were found." if empty else "",
        "model_reasoning_summary": combined_reasoning,
        "evidence": [],
    }
    await _emit_status(
        state,
        "sql_done",
        {"row_count": len(rows or []), "model": SQL_MODEL},
    )

    return {
        **state,
        "sql_text": sql_text,
        "sql_rationale": sql_rationale,
        "sql_reasoning": list(sql_reasoning or []),
        "response": response,
    }


# ---------------------------------------------------------------------------
# General node
# ---------------------------------------------------------------------------
async def node_general(state: StateSearch) -> StateSearch:
    query = state.get("query") or ""
    decision = state.get("decision") or {}
    await _emit_status(state, "general_start", {"query": query})

    general_payload, general_reasoning = await general_answer(query)
    route_note = f"Router chose general with confidence={float(decision.get('confidence', 0.0)):.3f}."
    combined_reasoning = list(general_reasoning or [])
    combined_reasoning.insert(0, route_note)

    response = {
        "query": query,
        "route": "general",
        "top_k": state.get("top_k"),
        "model": GENERAL_MODEL,
        "rerank_model": "router-general",
        "answer": general_payload.get("answer"),
        "confidence": general_payload.get("confidence"),
        "reasoning_summary": general_payload.get("reasoning_summary"),
        "citations": [],
        "limitations": general_payload.get("limitations"),
        "model_reasoning_summary": combined_reasoning,
        "evidence": [],
    }
    await _emit_status(state, "general_done", {"model": GENERAL_MODEL})

    return {
        **state,
        "general_payload": general_payload,
        "general_reasoning": list(general_reasoning or []),
        "response": response,
    }