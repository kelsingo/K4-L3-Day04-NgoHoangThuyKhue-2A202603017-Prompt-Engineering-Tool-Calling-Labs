from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chat import (
    ARTIFACTS_DIR,
    load_lab_env,
    run_model_tool_loop,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools


ROOT = Path(__file__).parent
load_lab_env(ROOT)

HTML = r"""
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PinkDesk — IT Helpdesk Agent</title>
  <style>
    :root {
      --pink-900: #831843;
      --pink-700: #be185d;
      --pink-600: #db2777;
      --pink-500: #ec4899;
      --pink-200: #fbcfe8;
      --pink-100: #fce7f3;
      --pink-50: #fdf2f8;
      --ink: #3b1830;
      --muted: #8b647b;
      --white: #fff;
      --shadow: 0 20px 60px rgba(190, 24, 93, .18);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 10% 10%, #fbcfe8 0, transparent 30%),
        radial-gradient(circle at 90% 80%, #f9a8d4 0, transparent 28%),
        linear-gradient(135deg, #fff7fb, #fdf2f8);
    }

    .app {
      width: min(1440px, 100%);
      min-height: 100vh;
      margin: auto;
      padding: 24px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 22px;
    }

    .panel {
      min-height: calc(100vh - 48px);
      overflow: hidden;
      border: 1px solid rgba(236, 72, 153, .18);
      border-radius: 28px;
      background: rgba(255, 255, 255, .82);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .chat-panel {
      display: flex;
      flex-direction: column;
    }

    header {
      padding: 26px 30px 22px;
      color: white;
      background: linear-gradient(135deg, var(--pink-900), var(--pink-600));
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .logo {
      width: 48px;
      height: 48px;
      display: grid;
      place-items: center;
      border-radius: 16px;
      background: rgba(255,255,255,.2);
      font-size: 25px;
    }

    h1, h2, p { margin: 0; }

    h1 {
      font-size: 22px;
      letter-spacing: -.02em;
    }

    .subtitle {
      margin-top: 5px;
      color: #fce7f3;
      font-size: 13px;
    }

    #messages {
      flex: 1;
      min-height: 420px;
      padding: 26px 30px;
      overflow-y: auto;
    }

    .empty {
      height: 100%;
      min-height: 350px;
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
    }

    .empty-icon {
      margin-bottom: 12px;
      font-size: 42px;
    }

    .message-row {
      display: flex;
      margin: 14px 0;
    }

    .message-row.user { justify-content: flex-end; }

    .bubble {
      max-width: min(78%, 760px);
      padding: 13px 16px;
      border-radius: 20px;
      white-space: pre-wrap;
      line-height: 1.55;
      font-size: 14px;
    }

    .message-row.user .bubble {
      color: white;
      border-bottom-right-radius: 5px;
      background: linear-gradient(135deg, var(--pink-600), var(--pink-500));
    }

    .message-row.assistant .bubble {
      border: 1px solid var(--pink-200);
      border-bottom-left-radius: 5px;
      background: var(--pink-50);
    }

    .composer {
      display: flex;
      gap: 12px;
      padding: 20px 30px 26px;
      border-top: 1px solid var(--pink-100);
      background: rgba(255,255,255,.75);
    }

    textarea {
      flex: 1;
      min-height: 54px;
      max-height: 150px;
      resize: vertical;
      padding: 15px 17px;
      color: var(--ink);
      border: 1px solid var(--pink-200);
      border-radius: 16px;
      outline: none;
      font: inherit;
      background: white;
    }

    textarea:focus {
      border-color: var(--pink-500);
      box-shadow: 0 0 0 4px rgba(236, 72, 153, .12);
    }

    button {
      cursor: pointer;
      border: 0;
      font: inherit;
      font-weight: 700;
    }

    #send {
      align-self: stretch;
      min-width: 104px;
      color: white;
      border-radius: 16px;
      background: linear-gradient(135deg, var(--pink-700), var(--pink-500));
      box-shadow: 0 8px 18px rgba(219, 39, 119, .25);
    }

    #send:disabled {
      cursor: wait;
      opacity: .55;
    }

    .side {
      display: flex;
      flex-direction: column;
      min-height: calc(100vh - 48px);
    }

    .side-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 22px;
      border-bottom: 1px solid var(--pink-100);
    }

    h2 {
      font-size: 16px;
    }

    #clear {
      padding: 8px 12px;
      color: var(--pink-700);
      border: 1px solid var(--pink-200);
      border-radius: 10px;
      background: white;
      font-size: 12px;
    }

    #logs {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      background: #fffafd;
    }

    .log {
      margin: 0 0 10px;
      padding: 11px 12px;
      border-left: 3px solid var(--pink-300);
      border-radius: 10px;
      background: white;
      box-shadow: 0 3px 12px rgba(131, 24, 67, .06);
      font-size: 12px;
    }

    .log-time {
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 10px;
    }

    .log-title {
      margin-bottom: 5px;
      color: var(--pink-700);
      font-weight: 800;
    }

    pre {
      max-height: 220px;
      margin: 7px 0 0;
      padding: 9px;
      overflow: auto;
      color: #54233e;
      border-radius: 8px;
      background: #fff1f8;
      font-size: 11px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .status {
      padding: 13px 22px;
      color: var(--muted);
      border-top: 1px solid var(--pink-100);
      font-size: 12px;
    }

    .dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      border-radius: 50%;
      background: #22c55e;
    }

    @media (max-width: 900px) {
      .app { grid-template-columns: 1fr; padding: 12px; }
      .panel, .side { min-height: auto; }
      .side { height: 420px; }
      .bubble { max-width: 90%; }
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="panel chat-panel">
      <header>
        <div class="brand">
          <div class="logo">💗</div>
          <div>
            <h1>PinkDesk Helpdesk Agent</h1>
            <p class="subtitle">IT support assistant · tool-calling workspace</p>
          </div>
        </div>
      </header>

      <div id="messages">
        <div class="empty" id="empty">
          <div>
            <div class="empty-icon">🌸</div>
            <strong>Bắt đầu cuộc trò chuyện</strong>
            <p style="margin-top:8px">Mô tả vấn đề IT cần hỗ trợ.</p>
          </div>
        </div>
      </div>

      <form class="composer" id="form">
        <textarea id="input" placeholder="Ví dụ: Kiểm tra trạng thái VPN production..." autofocus></textarea>
        <button id="send" type="submit">Gửi ↗</button>
      </form>
    </section>

    <aside class="panel side">
      <div class="side-head">
        <h2>Live activity log</h2>
        <button id="clear" type="button">Xóa log</button>
      </div>
      <div id="logs"></div>
      <div class="status"><span class="dot"></span><span id="status">Sẵn sàng</span></div>
    </aside>
  </main>

  <script>
    const messages = document.querySelector("#messages");
    const logs = document.querySelector("#logs");
    const empty = document.querySelector("#empty");
    const form = document.querySelector("#form");
    const input = document.querySelector("#input");
    const send = document.querySelector("#send");
    const statusText = document.querySelector("#status");
    let history = [];

    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    function addMessage(role, text) {
      empty.style.display = "none";
      const row = document.createElement("div");
      row.className = `message-row ${role}`;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = text || "(Không có nội dung)";
      row.appendChild(bubble);
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
    }

    function addLog(title, data) {
      const item = document.createElement("div");
      item.className = "log";

      const time = new Date().toLocaleTimeString("vi-VN");
      const timeEl = document.createElement("div");
      timeEl.className = "log-time";
      timeEl.textContent = time;

      const titleEl = document.createElement("div");
      titleEl.className = "log-title";
      titleEl.textContent = title;

      item.appendChild(timeEl);
      item.appendChild(titleEl);

      if (data !== undefined) {
        const pre = document.createElement("pre");
        pre.textContent = typeof data === "string" ? data : pretty(data);
        item.appendChild(pre);
      }

      logs.appendChild(item);
      logs.scrollTop = logs.scrollHeight;
    }

    function setBusy(value) {
      send.disabled = value;
      input.disabled = value;
      statusText.textContent = value ? "Agent đang xử lý..." : "Sẵn sàng";
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const text = input.value.trim();
      if (!text || send.disabled) return;

      addMessage("user", text);
      addLog("USER_MESSAGE", { message: text });
      input.value = "";
      setBusy(true);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ message: text, history })
        });

        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.error || "Request failed");
        }

        for (const round of payload.rounds || []) {
          addLog(`MODEL_ROUND_${round.round}`, {
            assistant_text: round.assistant_text,
            tool_calls: round.tool_calls
          });

          for (const event of round.tool_results || []) {
            addLog(`TOOL_RESULT · ${event.tool}`, event);
          }
        }

        addMessage("assistant", payload.assistant_text);
        addLog("ASSISTANT_RESPONSE", {
          status: payload.status,
          message: payload.assistant_text
        });

        history.push({role: "user", content: text});
        history.push({role: "assistant", content: payload.assistant_text});
      } catch (error) {
        addMessage("assistant", `Có lỗi xảy ra: ${error.message}`);
        addLog("ERROR", {message: error.message});
      } finally {
        setBusy(false);
        input.focus();
      }
    });

    document.querySelector("#clear").addEventListener("click", () => {
      logs.innerHTML = "";
      messages.innerHTML = "";
      messages.appendChild(empty);
      empty.style.display = "grid";
      history = [];
      addLog("SESSION_CLEARED");
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
  </script>
</body>
</html>
"""


class AppConfig:
    provider: Any
    tools: list[dict[str, Any]]
    model: str | None
    system_prompt: str
    max_tool_rounds: int


CONFIG: AppConfig | None = None


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        print(f"[ui] {format % args}")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_json(404, {"error": "Not found"})
            return

        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_json(404, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            user_text = str(payload.get("message", "")).strip()
            history = payload.get("history", [])

            if not user_text:
                self.send_json(400, {"error": "Message cannot be empty"})
                return

            if CONFIG is None:
                raise RuntimeError("UI is not configured")

            messages = [
                {"role": "system", "content": CONFIG.system_prompt},
                *history[-10:],
                {"role": "user", "content": user_text},
            ]

            print(f"\n[user] {user_text}")

            result = run_model_tool_loop(
                provider=CONFIG.provider,
                messages=messages,
                tools=CONFIG.tools,
                model=CONFIG.model,
                max_tool_rounds=CONFIG.max_tool_rounds,
            )

            print(f"[assistant] {result['assistant_text']}")
            for event in result.get("tool_events", []):
                print(f"[tool] {event['tool']}: {json.dumps(event, ensure_ascii=False)}")

            self.send_json(200, {
                "status": result.get("status"),
                "assistant_text": result.get("assistant_text", ""),
                "rounds": result.get("rounds", []),
                "tool_events": result.get("tool_events", []),
            })

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"[error] {error}")
            self.send_json(500, {"error": error})


def main() -> None:
    global CONFIG

    parser = argparse.ArgumentParser(description="Pink web UI for the IT Helpdesk Agent.")
    parser.add_argument(
        "--provider",
        choices=["openrouter", "openai", "anthropic", "gemini"],
        required=True,
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"

    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    declarations = load_tool_declarations(tools_path)

    CONFIG = AppConfig()
    CONFIG.provider = provider
    CONFIG.tools = to_openai_tools(declarations)
    CONFIG.model = selected_model
    CONFIG.system_prompt = system_prompt_path.read_text(encoding="utf-8")
    CONFIG.max_tool_rounds = args.max_tool_rounds

    server = ThreadingHTTPServer((args.host, args.port), RequestHandler)
    url = f"http://{args.host}:{args.port}"

    print(f"PinkDesk UI running at {url}")
    print(f"Provider: {args.provider}")
    print(f"Model: {selected_model}")
    print("Press Ctrl+C to stop.")

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PinkDesk UI...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()