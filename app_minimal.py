"""Minimal HTTP server with inline chat UI that talks to run_minimal.py via websocket."""
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8001
WS_PORT = 8766

HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>minimal agent</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: monospace; background: #1a1a1a; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }}
#log {{ flex: 1; overflow-y: auto; padding: 12px; white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.5; }}
#input-row {{ display: flex; border-top: 1px solid #333; }}
#input {{ flex: 1; background: #111; color: #e0e0e0; border: none; padding: 12px; font-family: monospace; font-size: 14px; outline: none; }}
#send {{ background: #333; color: #e0e0e0; border: none; padding: 12px 20px; cursor: pointer; font-family: monospace; font-size: 14px; }}
#send:hover {{ background: #444; }}
.user {{ color: #7aa2f7; }}
.agent {{ color: #9ece6a; }}
.tool {{ color: #e0af68; }}
.system {{ color: #565f89; }}
.thinking {{ display: inline-block; }}
.thinking::after {{ content: ''; animation: dots 1s steps(3) infinite; }}
@keyframes dots {{ 0% {{ content: '.'; }} 33% {{ content: '..'; }} 66% {{ content: '...'; }} }}
</style>
</head>
<body>
<div id="log"></div>
<div id="input-row">
  <input id="input" placeholder="ask the agent..." autofocus />
  <button id="send">send</button>
</div>
<script>
const log = document.getElementById('log');
const input = document.getElementById('input');
const send = document.getElementById('send');
let ws, thinkingEl;

function append(html, cls) {{
  const el = document.createElement('div');
  el.className = cls || '';
  el.innerHTML = html;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}}

function connect() {{
  ws = new WebSocket('ws://' + location.hostname + ':{WS_PORT}');
  ws.onopen = () => append('connected', 'system');
  ws.onclose = () => {{ append('disconnected — reconnecting...', 'system'); setTimeout(connect, 2000); }};
  ws.onmessage = (e) => {{
    const msg = JSON.parse(e.data);
    if (msg.type === 'user_echo') {{
      append('&gt; ' + escHtml(msg.content), 'user');
    }} else if (msg.type === 'text') {{
      if (thinkingEl) {{ thinkingEl.remove(); thinkingEl = null; }}
      append(escHtml(msg.content), 'agent');
    }} else if (msg.type === 'tool_use') {{
      if (!thinkingEl) thinkingEl = append('thinking', 'system thinking');
    }} else if (msg.type === 'done') {{
      if (thinkingEl) {{ thinkingEl.remove(); thinkingEl = null; }}
    }}
  }};
}}

function sendMsg() {{
  const text = input.value.trim();
  if (!text || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({{ type: 'user', content: text }}));
  input.value = '';
}}

function escHtml(s) {{ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

input.addEventListener('keydown', (e) => {{ if (e.key === 'Enter') sendMsg(); }});
send.addEventListener('click', sendMsg);
connect();
</script>
</body>
</html>"""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def log_message(self, *args):
        pass  # quiet


if __name__ == "__main__":
    print(f"Chat UI on http://0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
