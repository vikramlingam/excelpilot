# Security Policy

ExcelPilot is still under development. Treat it as a local-dev tool, not a hardened product.

## What this software does with data

- The FastAPI server binds to `127.0.0.1` by default (`EXCELPILOT_HOST` / `EXCELPILOT_PORT`).
- The add-in talks to that server over `/bridge` and `/chat`.
- Workbook contents are sent to OpenRouter when the chat model runs a turn.
- For destructive tools, a small structured state (tool name, args, user request) is sent to Jev: TypeSafe if `TYPESAFE_API_KEY` is set, otherwise OpenRouter System One. The Jev client drops keys named like `key` / `secret` / `token` / `password`, truncates long strings, and caps list samples at 5 items.
- Audit rows (tool name, hashed args, Jev scores) are stored in SQLite under `EXCELPILOT_DATA_DIR` (default `~/.excelpilot`).
- PDF bytes attached in the pane are parsed locally. If extraction is empty, a text snippet (not the PDF file) may be sent to OpenRouter as a vision fallback.

Do not point this at workbooks you would not paste into a model API. CORS on the API is currently `allow_origins=["*"]`.

## Supported versions

There is no supported production release. The tree you have is the only version.

## Reporting a vulnerability

Do not open a public GitHub issue for a security report.

Email aarvi.2705@gmail.com with what you found, how to reproduce it, and what it affects. Receipt within 48 hours is the aim, not a guarantee while this is a solo side project.

