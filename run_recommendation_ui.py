from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

from run_recommendation_pipeline import (
        DEFAULT_AGENT_MODEL,
        DEFAULT_COMPLIANCE_DB,
        DEFAULT_SUPPLIERS_DB,
        build_runtime_args,
        load_supplier_module,
        load_task3_module,
        process_prompt_with_runtime,
)


HTML = """<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Fleet Tire Agent UI</title>
    <style>
        :root {
            --fedex-purple: #4d148c;
            --fedex-orange: #ff6600;
            --bg: #f5f2fa;
            --ink: #241a33;
            --card: #ffffff;
            --muted: #6d6281;
            --line: #d8d0e5;
        }
        body {
            margin: 0;
            background:
                radial-gradient(circle at 10% 10%, rgba(255, 102, 0, 0.18) 0%, transparent 35%),
                radial-gradient(circle at 90% 0%, rgba(77, 20, 140, 0.18) 0%, transparent 40%),
                linear-gradient(150deg, #f9f7fc 0%, var(--bg) 55%);
            color: var(--ink);
            font-family: "Segoe UI", "Helvetica Neue", sans-serif;
            min-height: 100vh;
        }
        .wrap {
            max-width: 980px;
            margin: 40px auto;
            padding: 0 16px;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 14px;
            box-shadow: 0 16px 36px rgba(50, 22, 86, 0.14);
            padding: 0;
            overflow: hidden;
        }
        .topbar {
            height: 8px;
            background: linear-gradient(90deg, var(--fedex-purple) 0 70%, var(--fedex-orange) 70% 100%);
        }
        .content {
            padding: 20px;
        }
        h1 {
            margin: 0 0 8px;
            font-size: 1.6rem;
            letter-spacing: 0.2px;
        }
        .brand {
            display: inline-flex;
            align-items: baseline;
            gap: 2px;
            margin-bottom: 6px;
            font-weight: 800;
            font-size: 1rem;
            letter-spacing: 0.2px;
        }
        .brand .fed {
            color: var(--fedex-purple);
        }
        .brand .ex {
            color: var(--fedex-orange);
        }
        p {
            margin: 0 0 14px;
            color: var(--muted);
        }
        textarea {
            width: 100%;
            min-height: 96px;
            border-radius: 10px;
            border: 1px solid var(--line);
            padding: 12px;
            font-size: 14px;
            box-sizing: border-box;
            resize: vertical;
            background: #fff;
            color: var(--ink);
        }
        .row {
            display: flex;
            gap: 10px;
            margin-top: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        button {
            border: 0;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--fedex-purple), #6a2fa7);
            color: #fff;
            font-weight: 600;
            padding: 10px 16px;
            cursor: pointer;
            transition: transform 0.12s ease, box-shadow 0.12s ease;
        }
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 14px rgba(77, 20, 140, 0.3);
        }
        button:disabled {
            opacity: 0.6;
            cursor: default;
        }
        .hint {
            color: var(--muted);
            font-size: 13px;
        }
        pre {
            margin-top: 16px;
            background: #221738;
            color: #f5efff;
            border-radius: 10px;
            padding: 14px;
            overflow: auto;
            min-height: 220px;
            border: 1px solid #412266;
        }
    </style>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"card\">
            <div class=\"topbar\"></div>
            <div class=\"content\">
                <div class=\"brand\"><span class=\"fed\">Fed</span><span class=\"ex\">Ex</span></div>
                <h1>Fleet Tire Recommendation Agent</h1>
                <p>Example prompt: Need 24 tires size 225/70R19.5 load index 120 speed rating K in TX urgency medium for regional delivery and include compliance summary.</p>
                <textarea id=\"prompt\" placeholder=\"Enter your fleet request...\"></textarea>
                <div class=\"row\">
                    <button id=\"sendBtn\">Run Recommendation</button>
                    <label class=\"hint\"><input id=\"trajToggle\" type=\"checkbox\" /> Include trajectory</label>
                    <span class=\"hint\">Each request is logged in the server console.</span>
                </div>
                <pre id=\"out\">Awaiting input...</pre>
            </div>
        </div>
    </div>

    <script>
        const sendBtn = document.getElementById('sendBtn');
        const promptEl = document.getElementById('prompt');
        const trajToggle = document.getElementById('trajToggle');
        const out = document.getElementById('out');

        async function runPrompt() {
            const prompt = promptEl.value.trim();
            if (!prompt) {
                out.textContent = 'Please enter a prompt.';
                return;
            }

            sendBtn.disabled = true;
            out.textContent = 'Running...';
            try {
                const resp = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt, include_trajectory: Boolean(trajToggle.checked) }),
                });
                const payload = await resp.json();
                out.textContent = JSON.stringify(payload, null, 2);
            } catch (err) {
                out.textContent = `Request failed: ${err}`;
            } finally {
                sendBtn.disabled = false;
            }
        }

        sendBtn.addEventListener('click', runPrompt);
        promptEl.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                runPrompt();
            }
        });
    </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Run the Fleet Tire Agent web UI.")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8765)
        parser.add_argument("--agent-model", default=DEFAULT_AGENT_MODEL)
        parser.add_argument("--policy-version", default="policy-2026.06")
        parser.add_argument("--compliance-db", type=Path, default=DEFAULT_COMPLIANCE_DB)
        parser.add_argument("--suppliers-db", type=Path, default=DEFAULT_SUPPLIERS_DB)
        return parser.parse_args()


def main() -> int:
        options = parse_args()
        runtime_args = build_runtime_args(
                agent_model=options.agent_model,
                policy_version=options.policy_version,
                compliance_db=options.compliance_db,
                suppliers_db=options.suppliers_db,
        )
        task3 = load_task3_module()
        supplier = load_supplier_module()

        class Handler(BaseHTTPRequestHandler):
                def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
                        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
                        self.send_response(status)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)

                def do_GET(self) -> None:  # noqa: N802
                        if self.path in {"/", "/index.html"}:
                                body = HTML.encode("utf-8")
                                self.send_response(HTTPStatus.OK)
                                self.send_header("Content-Type", "text/html; charset=utf-8")
                                self.send_header("Content-Length", str(len(body)))
                                self.end_headers()
                                self.wfile.write(body)
                                return
                        self.send_error(HTTPStatus.NOT_FOUND)

                def do_POST(self) -> None:  # noqa: N802
                    if self.path != "/api/prompt":
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return

                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length)
                    try:
                        request_payload = json.loads(raw.decode("utf-8")) if raw else {}
                        prompt = str(request_payload.get("prompt", "")).strip()
                        include_trajectory = bool(request_payload.get("include_trajectory", False))
                    except Exception:
                        self._send_json({"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
                        return

                    if not prompt:
                        self._send_json({"error": "prompt_required"}, status=HTTPStatus.BAD_REQUEST)
                        return

                    request_args = build_runtime_args(
                        agent_model=runtime_args.agent_model,
                        policy_version=runtime_args.policy_version,
                        compliance_db=runtime_args.compliance_db,
                        suppliers_db=runtime_args.suppliers_db,
                        show_trajectory=include_trajectory,
                    )

                    code, output = process_prompt_with_runtime(
                        prompt,
                        args=request_args,
                        task3_module=task3,
                        supplier_module=supplier,
                        source="web-ui",
                    )
                    if output is None:
                        self._send_json({"error": "no_output"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                        return
                    status = HTTPStatus.OK if code == 0 else HTTPStatus.BAD_REQUEST
                    self._send_json(output, status=status)

                def log_message(self, format: str, *args: object) -> None:
                        return

        server = ThreadingHTTPServer((options.host, options.port), Handler)
        print(f"[ui] Fleet Tire Agent UI running at http://{options.host}:{options.port}")
        print("[ui] Press Ctrl+C to stop")
        try:
                server.serve_forever()
        except KeyboardInterrupt:
                pass
        finally:
                server.server_close()
                print("[ui] Server stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
