# Bank statement AI import — outage diagnosis

**Date:** 2026-09-15
**Symptom reported:** Bank statement "Paste or type bank transactions" import fails.
UI shows `gemini-3.6-flash returned nothing — try again to use the next model`,
and after retrying, "tried all the models failed."

## TL;DR

Not a code bug and not a server outage. **Every model in the AI rotation ring is
dead** because of two independent, external problems:

1. **Groq** model `llama-3.3-70b-versatile` was **decommissioned** (404). The Groq
   key is still valid.
2. **Gemini** project behind `GEMINI_API_KEY` is **banned by Google** (403
   `PERMISSION_DENIED` — "Your project has been denied access") on all
   `generateContent` calls. The model ids themselves are valid.

## How the error is produced

`app/service/acc/o_bank_ai.py` uses a hard round-robin rotation (no in-call
fallback, no retry). Each import click draws the next model and advances a global
cursor. The ring comes from `settings.AI_ROTATION_MODELS` (`app/config.py`):

```
groq:llama-3.3-70b-versatile
gemini:gemini-3.6-flash
gemini:gemini-3.5-flash
```

When a model call throws, it's caught at `o_bank_ai.py:197`, `raw` becomes `""`,
and `interpret_bank_text` raises 502 with `f"{model_used} returned nothing — try
again to use the next model"` (`o_bank_ai.py:342-346`). Retrying just advances to
the next (also-dead) model → "tried all the models failed."

## Evidence (tested 2026-09-15 against the keys in `a:/toocore/.env`)

### Remote backend is UP (not the problem)
`https://toocore.fastapicloud.dev`
- `GET /openapi.json` → **200**
- `GET /acc/o_bankstatement/get_list` → **401** (route exists, needs auth)
- `POST /acc/o_bankstatement/interpret_stream` (no auth) → **401** (route exists)

(An earlier `HTTP 000` / `curl error 43` was a Windows curl + schannel quirk with
`-w`, not an outage. Forcing `-4 --http1.1 -v` showed real HTTP responses.)

### Groq — key valid, model gone
`POST https://api.groq.com/openai/v1/chat/completions` with
`llama-3.3-70b-versatile`:
```
HTTP 404
{"error":{"message":"The model `llama-3.3-70b-versatile` does not exist or you do
not have access to it.","type":"invalid_request_error","code":"model_not_found"}}
```
`GET /openai/v1/models` returned 200 with 13 models. Current usable **text** models
on this key: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`,
`openai/gpt-oss-safeguard-20b`, `qwen/qwen3.8-27b`, `groq/compound`,
`groq/compound-mini`, `allam-2-7b`. (whisper = audio, prompt-guard = moderation,
orpheus = TTS — not usable for JSON generation.)

### Gemini — project banned
`POST .../v1beta/models/{id}:generateContent` for `gemini-3.6-flash` and
`gemini-3.5-flash`:
```
HTTP 403
{"error":{"code":403,"message":"Your project has been denied access. Please
contact support.","status":"PERMISSION_DENIED"}}
```
`gemini-2.5-flash` → **404** "no longer available to new users ... use
gemini-3.6-flash". So the ids in config are current; the project itself is blocked.

`ListModels` (metadata) still succeeds and lists `gemini-3.5-flash`,
`gemini-3.6-flash`, etc. — which is why the model ids *look* fine. Only
`generateContent` is denied.

## Fixes (different owners)

1. **Groq (code, ~1 line):** replace `llama-3.3-70b-versatile` with a current id
   (e.g. `openai/gpt-oss-120b`) in `AI_ROTATION_MODELS` and `GROQ_MODEL_ID` in
   `app/config.py`. Restores a working leg of the rotation on its own.
2. **Gemini (account, NOT code):** the project is banned — no code change fixes it.
   Need a **new/unbanned `GEMINI_API_KEY`** (fresh Google Cloud project) or resolve
   the ban with Google support. Until then, consider dropping the two Gemini entries
   from the ring so imports don't fail ~2 of every 3 attempts.

## Caveats

- Tested against the **local `.env`** keys. The **deployed** instance may hold
  different secrets (can't read them). The reported error string matches the local
  key's 403 exactly, so they're almost certainly the same banned project. To confirm
  on the deployed instance, reproduce through the live endpoint with a valid Supabase
  user token.
- **Any code fix must be redeployed** to `toocore.fastapicloud.dev`. The React apps
  point at the remote in both `.env.development` and `.env.production`
  (`VITE_CORE_API=https://toocore.fastapicloud.dev`), so local edits don't affect
  live testing until deployed.
