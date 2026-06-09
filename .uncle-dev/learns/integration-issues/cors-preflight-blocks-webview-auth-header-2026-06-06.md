---
module: apps/backend/server.py
tags: [cors, preflight, tauri, webview, fetch, x-squirrel-token, onboarding, obsidian]
problem_type: integration-issue
date: 2026-06-06
---

# CORS preflight silently blocks the webview's authenticated fetch

## Symptom
The desktop onboarding wizard ("the installer") always showed **"Obsidian not
found"**, even though Obsidian was installed at `/Applications/Obsidian.app`.
The menu-bar/tray deadlines rendered fine.

## The trap (why it was hard to find)
- `curl http://127.0.0.1:3939/api/env/obsidian -H "X-Squirrel-Token: <tok>"`
  returned `{"installed": true}`. **curl does not perform a CORS preflight**, so
  it never exercised the failing path. Hours were spent "proving the backend
  works" with curl while the real (browser) path was broken.
- The menu-bar deadlines work because the **tray is rendered by Rust/reqwest**
  (server-side, no browser CORS) — only the **React webview's `fetch`** is
  subject to CORS. So "the app shows data" did not mean the webview worked.

## Root cause
The webview (`tauri://localhost`, or `http://localhost:1420` in dev) calls the
backend on `http://127.0.0.1:3939` — cross-origin. Every request carries the
custom `X-Squirrel-Token` auth header, which is **not** a CORS-safelisted
header, so the browser sends a **preflight `OPTIONS`** first. The backend's
`do_OPTIONS` answered:

    Access-Control-Allow-Headers: Content-Type

`X-Squirrel-Token` was missing → the browser **failed the preflight and blocked
the real request before sending it** → `fetch` rejected → the wizard's
`.catch` rendered "not found". The access log showed *no* request arriving
(it was blocked client-side), which was itself a clue.

## Fix
`apps/backend/server.py` `do_OPTIONS`:

    Access-Control-Allow-Headers: Content-Type, X-Squirrel-Token

Any custom (non-safelisted) request header the webview sends MUST be echoed in
`Access-Control-Allow-Headers`, or the browser blocks the request.

## How to reproduce / test without a browser
Simulate the preflight explicitly (curl normally skips it):

    curl -i -X OPTIONS \
      -H "Origin: tauri://localhost" \
      -H "Access-Control-Request-Method: GET" \
      -H "Access-Control-Request-Headers: x-squirrel-token,content-type" \
      http://127.0.0.1:3939/api/env/obsidian

The response's `Access-Control-Allow-Headers` must contain `x-squirrel-token`.
Regression test: `TestCorsPreflight` in `apps/cli/tests/test_web_ui_server.py`.

## Takeaway
When a browser/webview request "works in curl but fails in the app", suspect
**CORS preflight** for custom headers/methods/content-types. Test the OPTIONS
preflight directly; don't trust curl on the GET.
