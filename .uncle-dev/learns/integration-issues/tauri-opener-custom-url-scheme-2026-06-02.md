---
title: "Tauri v2: opener:default blocks custom URL schemes; add scoped opener:allow-open-url"
date: 2026-06-02
category: integration-issues
module: desktop-app
problem_type: integration_issue
component: tooling
severity: medium
symptoms:
  - openUrl() with a custom scheme (e.g. obsidian://) silently does nothing
  - No JS error, no Tauri event — call appears to succeed but the target app never opens
  - Standard https:// URLs work correctly with the same openUrl() call
root_cause: missing_permission
resolution_type: config_change
tags: [tauri, capabilities, opener, custom-url-scheme, obsidian, silent-failure, scope, allow-default-urls]
---

# Tauri v2: opener:default blocks custom URL schemes; add scoped opener:allow-open-url

## Problem

Calling `openUrl("obsidian://open?vault=vault-tdah")` from the React frontend did nothing. The same function worked correctly for `https://` URLs. No error was surfaced anywhere.

## Symptoms

- Button calling `openUrl("obsidian://...")` has no visible effect
- `openUrl("https://...")` works correctly with the same `opener:default` permission
- No JS exception, no Tauri error event — call appears to succeed silently

## What Didn't Work

Assuming `opener:default` covers all URL schemes. `opener:default` includes `allow-default-urls`, whose `scope.allow` is explicitly restricted to `mailto:*`, `tel:*`, `http://*`, `https://*`. Confirmed by reading `gen/schemas/acl-manifests.json`:

```json
"allow-default-urls": {
  "scope": {
    "allow": [
      { "url": "mailto:*" },
      { "url": "tel:*" },
      { "url": "http://*" },
      { "url": "https://*" }
    ]
  }
}
```

Any scheme outside this array is silently denied at the IPC boundary — no error reaches the caller.

## Solution

`apps/desktop/src-tauri/capabilities/default.json`

```json
"permissions": [
  "opener:default",
  {
    "identifier": "opener:allow-open-url",
    "allow": [{ "url": "obsidian://**" }]
  }
]
```

No frontend code change required.

## Why This Works

Tauri v2 merges permission scopes with union semantics: a URL is permitted if it matches any `allow` entry across all active permissions for that command. Adding a scoped `opener:allow-open-url` for `obsidian://**` extends the allowed set without replacing `allow-default-urls` — http/https/mailto/tel remain covered. The `**` glob matches any path and query string under the scheme.

The silent failure is by design: Tauri v2 denies out-of-scope calls at the IPC boundary before they reach Rust, and does not propagate an error to the caller.

## Prevention

- Every `openUrl()` call with a non-http/https scheme requires an explicit scoped entry in capabilities. `opener:default` does not cover custom schemes.
- "Does nothing, no error" is the canonical Tauri v2 symptom of an IPC denial. When a button does nothing, check capabilities first.
- Do not rely on documentation for permission scope arrays — read `gen/schemas/acl-manifests.json` directly. It is the ground truth and the Tauri docs can lag.
- Consider a comment block in `capabilities/default.json` listing all intentionally allowed custom schemes, so the list is easy to audit and extend.

## Related Issues

- [`tauri-window-close-vs-hide-2026-06-02.md`](tauri-window-close-vs-hide-2026-06-02.md) — same silent-failure pattern from a missing `core:window:allow-close` capability
