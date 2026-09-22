# DB Connection & Tenancy Review — 2026-07-05

Session summary: Aiven Postgres capacity review, connection-pool cleanup, and a
security review of the admin-engine (RLS-bypass) endpoints — plus the intentional
tenant-model design that came out of the discussion.

---

## 1. Aiven service facts (`tooproj` / `pgservice`)

- Plan: **`free-1-1gb`** ($0). PostgreSQL **17.10**, cloud `do-sfo` (DigitalOcean SF), single node (no HA).
- Free-tier limits:
  - Disk **1 GB**, RAM 1 GB, 1 vCPU
  - **max_connections = 20** ← the tightest real constraint
  - No PgBouncer, no service integrations (metrics/logs), no PITR (daily full backup only)
- **Usage at review time:** ~40 MB of 1 GB (~4%). Databases: `toodb` 16MB, `defaultdb` ~8MB,
  `agentcoredb` ~8MB, `_aiven` ~8MB. Live client connections: 2/20.
- Storage/compute are not the concern; **the 20-connection cap is**.

### Connection-count concepts clarified
- A "connection" = one live TCP/socket session, **not** a user and **not** a dburl.
  Same dburl opened N times = N connections. Different users don't merge either.
- End users hit the FastAPI backend over HTTP; the **backend** holds the DB pool.
  1000 users ≠ 1000 DB connections. The cap applies to: sum of every pool across
  every running process + ad-hoc sessions (psql, cron, admin tools).
- Closing per-fetch frees the slot but adds reconnect latency (TCP+TLS+SCRAM ~20–100ms).
  The right pattern is a bounded app-side pool, sized well under 20.

---

## 2. Connection-pool cleanup (DONE this session)

### Problem
5 SQLAlchemy engines existed across 3 files. Default async pool = `pool_size=5 + max_overflow=10`
= up to **15 conns per engine** → up to **75 potential** vs a **20 cap**. Even idle baseline
(5×5=25) already exceeded 20.

Root cause (from git history): **NOT SQLModel leftovers** (SQLModel fully removed, zero imports).
The duplicates were **pre-RLS / pre-Aiven SupaBase-era scaffold** (`db_async.py` originally used
`settings.TOO_SB_DB`), carried forward and re-pointed at Aiven. Each new feature commit
(`rls`, `db_core`) added a new file with its own `create_async_engine` instead of importing
an existing one.

### Engine inventory (before)
| Engine | File | Status |
|--------|------|--------|
| `too_async_engine` | db_async.py:13 | dead (fed only dead `get_session`) |
| `async_engine_admin` | db_async.py:24 | live — `get_db_admin` |
| `async_engine_admin` | pgconn.py:32 | live — `get_admin_conn` (dup of same URL) |
| `async_engine_rls` | pgconn.py:31 | live — `get_rls_conn` |
| `async_engine_rls` | db_rls_orm.py:30 | dead (all `get_pgconn` callers commented out) |

### Changes made
- **`db_async.py`** — rewritten as the single source of truth for the ADMIN engine.
  Deleted dead `too_async_engine` + `get_session`. Pool capped **1 + 2 = 3**.
- **`pgconn.py`** — removed its duplicate admin engine; now imports the shared `admin_engine`
  from `db_async`. RLS engine capped **8 + 4 = 12**. `pool_recycle=1800` added to both.
- **`db_rls_orm.py`** — **deleted** (fully dead).

### Result (verified at runtime)
- admin_engine pool size 1 / overflow 2; rls_engine 8 / overflow 4.
- `pgconn.admin_engine is db_async.admin_engine` → **True** (genuinely shared, not copied).
- **2 engines, hard max 15 connections** (steady ~9), comfortably under 20 with ~5 headroom.

---

## 3. Admin-engine (RLS-bypass) security review

**Key principle:** on `get_db_admin` / `get_admin_conn`, queries run as `avnadmin` and
**RLS is bypassed entirely**. The only cross-tenant protection is manual per-query filtering.

### Scope decision
User will migrate all admin endpoints EXCEPT provisioning back to `get_rls_conn` after dev.
So only **`too1 /new_user_provision_seed`** was reviewed in depth as the endpoint that
legitimately stays on admin (creating a tenant's first rows, before any JWT tenant context
exists — RLS can't apply yet).

### Findings on `too1` provisioning
- **Auth is solid.** JWT verified via JWKS (signature + `aud` + `iss` + `alg`, `auth.py:116`).
  `zuid` comes from signed `sub` claim → caller cannot forge which user is provisioned.
- **Admin use is justified** for this endpoint.
- **Finding 1 (atomicity):** SQL inserts are wrapped in `conn.begin()` (rolls back on error),
  but `updateid_ten_cli()` writes to Supabase *after* commit. On failure the idempotency
  guard (checks `ZUserClientDB` by id) self-heals via the early-return branch on next login.
  Gap: `apply_seed_defaults` idempotency not verified. **Status: TOLERATED for now (user decision).**
- **Finding 3 (race):** concurrent double-signup both pass the existence check then insert;
  `on_conflict_do_nothing/do_update` prevents dup-key crashes, but seed idempotency is the
  linchpin. Not addressed — acceptable at current stage.
- **Minor:** unused import `update_sbu_be` in `too2_me.py:8`; dead commented endpoints in
  `too1` (lines 17–36); `zuid` used as UUID PK without `_uuid_or_none` normalization
  (inconsistent with `ztid`).

### Other admin endpoints (NOT fixed — will move to RLS post-dev)
Recorded for the migration, not acted on:
- 🔴 `mcp /bank/query` (`too_mcp_callback.py:77`): **no auth dependency, no tenant scoping** —
  `get_recent_bank_transactions` filters by `account_name` string only; `BankTransactionMCPDB`
  has no tenant column. Cross-tenant exposure if reachable. `/vendors/lookup` same structural gap (stubbed).
- 🔴 `ser_employee.create_or_update_employee` (`ser_employee.py:24`): references undefined
  `zuid` (should be `zjwt.zuid`) → `NameError` on the employee-create path.
- Scoped-OK admin endpoints today: `getme/saveme` (by `id==zuid`), `getbe/savebe` (by `zuid`),
  `get_employee_list` (by `cli_id==zcid`).

---

## 4. Tenant model — INTENTIONAL DESIGN (confirmed by user)

This is the non-obvious architecture that the code alone doesn't explain.

- At provisioning: `ten_id = biz_id = usr_id = cli_id = created_by = zuid`
  (`ser1_new_user.py:101`). **Every signup is a self-contained one-person organization.**
  Target market is SME, so "one user = one org" is the default, by design — not a limitation.
- `ten_id` is a **mutable column, not the PK** (PK is `id == zuid`). Growth path: an admin can
  reassign a user's `ten_id` to an existing tenant → the user becomes an "employee" of a
  larger org. Identity (PK) stays stable while tenancy moves.
- RLS scopes on `sba_ten_id` from the JWT, so flipping `ten_id` + the JWT claim automatically
  re-scopes the user to the new tenant with **no query rewrites**.
- **Seed data = a personal learning sandbox.** No business meaning. It exists so a new user can
  explore the system under their own tenant.
- **On reassignment, seed rows intentionally stay behind** under the user's original
  `zuid`-tenant. This is BY DESIGN, not orphaned data:
  - Before reassignment: the user learns the system in their own solo-org sandbox.
  - On being assigned a new `ten_id`: they intentionally start from a **brand-new clean
    environment** (the real tenant's data), with none of their practice data bleeding in.
  - RLS keeps the old sandbox fully isolated from the joined org.
- Consequence: reassignment is effectively a **one-field operation** (flip JWT `sba_ten_id`);
  there is deliberately **no data migration** to perform.

### Known/accepted parking lot
- Supabase + Aiven have some integration issues; explicitly **not being dealt with now**.
- Finding 1 (provisioning atomicity across DB+Supabase) tolerated for now.

---

_Connection cleanup was applied and verified. The security findings on non-provisioning admin
endpoints are recorded for the planned post-dev migration to RLS, not yet fixed._
