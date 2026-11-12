#!/usr/bin/env python3
"""Local-only live dashboard for the PDUFA Windows engineering worker.

Read-only except for an explicit, CSRF-protected owner STOP request. Never
starts, merges, deploys, rates clinical studies or edits the progress ledger.
Run: py -3.13 scripts\windows_local_agent_dashboard.py --open
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
import webbrowser

HOME = Path.home() / "PDUFA-Agent-Continuous"
LEDGER = HOME / "ledger.json"
HEARTBEAT = HOME / "heartbeat.json"
LOCK = HOME / "RUNNING.lock"
STOP = HOME / "STOP"
HOST = "127.0.0.1"
PORT = 8765
TOTAL = 17
VALID_STATUS = {"PENDING", "RUNNING", "DRAFT_PR_CREATED", "BLOCKED"}
PR_PREFIX = "https://github.com/pdufa/pdufa-command-center/pull/"

PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PDUFA / Live Development</title>
  <style>
    :root {color-scheme:dark;--bg:#080e1b;--panel:#101b2d;--panel2:#152238;
      --border:#26374d;--text:#eff7ff;--muted:#92a8c1;--green:#50e3b0;
      --gold:#eeca82;--blue:#72b6ff;--red:#ff8b91}
    *{box-sizing:border-box}
    body{margin:0;background:radial-gradient(ellipse 90% 60% at 95% -5%,#183653 0%,transparent 65%),var(--bg);
      color:var(--text);font-family:Segoe UI,Inter,Arial,sans-serif;line-height:1.5}
    .shell{max-width:1260px;margin:auto;padding:30px 24px 70px}
    .mast{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;
      border-bottom:1px solid var(--border);padding-bottom:18px}
    .logo{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:.13em;font-size:13px}
    .mark{display:grid;place-items:center;background:var(--green);color:#09251d;width:35px;height:35px;
      border-radius:11px;font-size:19px}
    .muted{color:var(--muted)} .small{font-size:12px}
    .pill{border:1px solid var(--border);padding:8px 12px;border-radius:100px;color:var(--muted);
      font-size:12px;font-weight:700;letter-spacing:.04em}
    .pill.live{border-color:#26725f;color:var(--green);background:#102f2d}
    .pill.warn{border-color:#8c663c;color:var(--gold);background:#302616}
    .pill.stop{border-color:#854550;color:var(--red);background:#311e28}
    .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:currentColor;margin-right:7px}
    .pill.live .dot{animation:pulse 1.5s infinite}
    @keyframes pulse{50%{box-shadow:0 0 0 7px #50e3b020}}
    h1{font-size:clamp(32px,5vw,56px);letter-spacing:-.045em;line-height:1.1;margin:25px 0 9px}
    .subtitle{margin:0 0 25px;color:var(--muted);max-width:770px}
    .layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(285px,1fr);gap:17px}
    .panel{background:linear-gradient(160deg,#122037,#0d182a);border:1px solid var(--border);
      border-radius:19px;padding:23px;min-width:0}
    .eyebrow{font-size:11px;font-weight:800;color:var(--muted);letter-spacing:.14em;text-transform:uppercase}
    .big{font-size:52px;letter-spacing:-.05em;font-weight:800;line-height:1.2;margin:8px 0}
    .big span{font-size:22px;color:var(--muted);font-weight:500}
    .progress-labels{display:flex;justify-content:space-between;gap:10px;margin:20px 0 10px;font-size:13px}
    .progress{display:flex;gap:4px;height:19px;overflow:hidden;border-radius:6px}
    .segment{flex:1;background:#27364b;transition:background .2s}
    .segment.done{background:var(--green)}.segment.active{background:var(--blue);animation:pulsebar 1.3s infinite alternate}
    .segment.blocked{background:var(--red)}
    @keyframes pulsebar{to{opacity:.6}}
    .note{color:var(--muted);font-size:12px;margin:18px 0 0}
    .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
    .stat{background:#101d31;border:1px solid var(--border);border-radius:14px;padding:16px}
    .stat strong{font-size:29px;display:block;line-height:1.35}
    .stat small{color:var(--muted)}
    .section-heading{display:flex;justify-content:space-between;gap:12px;align-items:center;
      margin:30px 0 14px}
    h2{margin:0;font-size:21px;letter-spacing:-.02em}
    .stages{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .stage{border:1px solid var(--border);background:var(--panel);border-radius:13px;
      padding:14px;display:flex;gap:13px;align-items:flex-start;min-width:0}
    .stage.done{border-color:#255a52}.stage.active{border-color:#427aa3;background:#122741}
    .stage.blocked{border-color:#7c4350}
    .number{width:39px;height:39px;flex:0 0 39px;border-radius:11px;background:#23364d;
      display:grid;place-items:center;font-weight:800;color:#c9e0f6;font-size:14px}
    .stage.done .number{color:#051f18;background:var(--green)}.stage.active .number{background:#286395}
    .stage.blocked .number{background:#773745}
    .stage-main{min-width:0;flex:1}
    .stage-name{font-size:13px;font-weight:700;overflow-wrap:anywhere}
    .tag{color:var(--muted);font-size:11px;font-weight:800;letter-spacing:.06em;margin:3px 0}
    .stage.done .tag{color:var(--green)}.stage.active .tag{color:var(--blue)}
    .stage.blocked .tag{color:var(--red)}
    a{color:#9fd0ff;text-decoration:none}a:hover{text-decoration:underline}
    .stage a{font-size:12px;display:inline-block;margin-top:4px}
    .info{display:flex;justify-content:space-between;gap:14px;padding:14px 0;border-bottom:1px solid var(--border)}
    .info:last-child{border-bottom:0}
    .info span:first-child{color:var(--muted);font-size:13px}
    .info strong{font-size:13px;text-align:right;overflow-wrap:anywhere}
    .btn{background:#223c53;border:1px solid #44617a;border-radius:10px;color:#e7f6ff;
      padding:11px 15px;font:700 13px Segoe UI,Arial,sans-serif;cursor:pointer}
    .btn:hover{background:#2b4d68}
    .btn.danger{background:transparent;border-color:#77444b;color:#ffb6ba}
    .btn.danger:hover{background:#39232b}
    .actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:23px}
    .notice{font-size:12px;color:var(--muted);margin-top:13px}
    .error{color:var(--red)}
    .footer{font-size:12px;color:var(--muted);margin-top:26px;border-top:1px solid var(--border);padding-top:18px}
    @media(max-width:850px){.layout{grid-template-columns:1fr}.stages{grid-template-columns:1fr}}
    @media(max-width:480px){.shell{padding:15px}.panel{padding:17px}.stats{gap:7px}.stat{padding:11px}.big{font-size:43px}}
  </style>
</head>
<body>
<main class="shell">
  <header class="mast">
    <div class="logo"><div class="mark">P</div><div>PDUFA <span class="muted">/ COMMAND CENTER</span></div></div>
    <div class="pill" id="health"><span class="dot"></span>CONNECTING TO LOCAL WORKER</div>
  </header>
  <h1>Live development<span style="color:var(--green)">.</span></h1>
  <p class="subtitle">A window into your Windows engineering worker. Status updates every 3 seconds. All stages below represent <strong>draft engineering artifacts</strong>, not approved scientific assessments.</p>
  <div class="layout">
    <section class="panel" aria-label="Engineering draft progress">
      <div class="eyebrow">Stages 04 — 20 / Engineering draft PRs</div>
      <div class="big"><span id="count">—</span><span> / 17</span></div>
      <div class="progress-labels"><strong id="percent">—%</strong><span class="muted" id="completed-label">Waiting for progress ledger</span></div>
      <div class="progress" id="progress" role="progressbar" aria-valuemin="0" aria-valuemax="17" aria-valuenow="0" aria-label="Verified draft PRs created"></div>
      <p class="note">Green = draft PR created · Blue = currently drafting · Red = blocked · Gray = pending. Reaching 17/17 does <strong>not</strong> mean scientific Levels 4–20 have been validated.</p>
      <div class="stats">
        <div class="stat"><small>Draft PRs</small><strong id="drafts">—</strong></div>
        <div class="stat"><small>Pending</small><strong id="pending">—</strong></div>
        <div class="stat"><small>Blocked</small><strong id="blocked">—</strong></div>
      </div>
    </section>
    <aside class="panel" aria-label="Live worker details">
      <div class="eyebrow">Live worker telemetry</div>
      <div class="info"><span>Current task</span><strong id="current">—</strong></div>
      <div class="info"><span>Worker heartbeat</span><strong id="heartbeat">—</strong></div>
      <div class="info"><span>Last activity</span><strong id="activity">—</strong></div>
      <div class="info"><span>Work queue</span><strong id="queue">—</strong></div>
      <div class="info"><span>Science levels verified</span><strong>0 / 20 — not validated</strong></div>
      <div class="info"><span>Production deployments</span><strong>Disabled</strong></div>
      <div class="actions">
        <a class="btn" href="https://github.com/pdufa/pdufa-command-center/pulls" target="_blank" rel="noopener noreferrer">View draft PRs ↗</a>
        <button class="btn danger" id="stop" type="button">Request safe stop</button>
      </div>
      <p class="notice" id="message">A stop request lets the current bounded task finish and prevents the next one. It never merges or deploys code.</p>
    </aside>
  </div>
  <div class="section-heading"><h2>Stage-by-stage activity</h2><span class="muted small" id="refreshed">Not refreshed yet</span></div>
  <section class="stages" id="stages" aria-label="Stages 4 through 20"></section>
  <footer class="footer">LOCAL DASHBOARD · 127.0.0.1 ONLY · NO CLOUD SERVER · No automatic merges, production deployments, or clinical prediction updates. Close this window to stop viewing; the development worker continues separately.</footer>
</main>
<script nonce="__TOKEN__">
(function () {
  'use strict';
  var TOKEN = '__TOKEN__';
  var STAGES = document.getElementById('stages');
  var PROGRESS = document.getElementById('progress');
  function setText(id, value) { document.getElementById(id).textContent = String(value); }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function node(tag, cls, value) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (value !== undefined) n.textContent = String(value);
    return n;
  }
  function fmtTime(value) {
    if (!value) return '—';
    var date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toLocaleString() : '—';
  }
  function draw(data) {
    var totals = data.totals;
    var health = document.getElementById('health');
    health.className = 'pill ' + (data.worker.state === 'LIVE' ? 'live' :
      data.worker.state === 'STOP_REQUESTED' ? 'stop' : 'warn');
    health.replaceChildren(node('span', 'dot'), document.createTextNode(' ' + data.worker.label));
    setText('count', totals.drafts);
    setText('drafts', totals.drafts);
    setText('pending', totals.pending);
    setText('blocked', totals.blocked);
    setText('percent', Math.round(totals.drafts / 17 * 100) + '%');
    setText('completed-label', totals.drafts + ' verified draft PRs of 17 engineering tasks');
    PROGRESS.setAttribute('aria-valuenow', String(totals.drafts));
    clear(PROGRESS);
    clear(STAGES);
    data.stages.forEach(function (stage) {
      var className = stage.status === 'DRAFT_PR_CREATED' ? 'done' :
        stage.status === 'RUNNING' ? 'active' : stage.status === 'BLOCKED' ? 'blocked' : '';
      var segment = node('div', 'segment ' + className);
      segment.title = 'Level ' + stage.level + ': ' + stage.status;
      PROGRESS.appendChild(segment);
      var card = node('article', 'stage ' + className);
      card.appendChild(node('div', 'number', String(stage.level).padStart(2, '0')));
      var main = node('div', 'stage-main');
      main.appendChild(node('div', 'stage-name', stage.name));
      var status = stage.status === 'DRAFT_PR_CREATED' ? 'DRAFT PR CREATED' :
        stage.status === 'RUNNING' ? 'WORKING · ATTEMPT ' + stage.attempts :
        stage.status === 'BLOCKED' ? 'BLOCKED · ' + (stage.blocker || 'REVIEW REQUIRED') : 'QUEUED';
      main.appendChild(node('div', 'tag', status));
      if (stage.pr) {
        var link = node('a', '', 'Open draft pull request ↗');
        link.href = stage.pr;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        main.appendChild(link);
      }
      card.appendChild(main);
      STAGES.appendChild(card);
    });
    setText('current', data.worker.state === 'LIVE' && totals.running ?
      'Level ' + String(totals.running).padStart(2, '0') : data.worker.label);
    setText('heartbeat', data.worker.age_seconds === null ? 'Not available' :
      data.worker.age_seconds + 's ago · ' + data.worker.mode);
    setText('activity', fmtTime(data.last_activity));
    setText('queue', totals.pending + ' pending · ' + totals.blocked + ' blocked');
    setText('refreshed', 'Last checked ' + new Date().toLocaleTimeString());
    document.getElementById('stop').disabled = data.worker.state === 'STOP_REQUESTED';
  }
  async function refresh() {
    try {
      var response = await fetch('/api/status', {cache:'no-store'});
      if (!response.ok) throw new Error('Unable to read local status');
      draw(await response.json());
    } catch (error) {
      var pill = document.getElementById('health');
      pill.className = 'pill stop';
      pill.textContent = 'LOCAL DASHBOARD DISCONNECTED';
      setText('message', 'Cannot read local worker data. The coding process is separate from this dashboard.');
    }
  }
  document.getElementById('stop').addEventListener('click', async function () {
    if (!window.confirm('Request a graceful STOP of continuous development after the current bounded task? This does not stop the dashboard.')) return;
    try {
      var response = await fetch('/api/stop', {method:'POST', headers:{'X-PDUFA-Dashboard-Token':TOKEN}});
      if (!response.ok) throw new Error('Stop request was not accepted');
      setText('message', 'STOP REQUESTED. The worker will finish its bounded task, then stop. No new tasks will begin.');
      refresh();
    } catch (error) { setText('message', 'STOP REQUEST FAILED. Use the Windows installer -Stop command.'); }
  });
  refresh();
  window.setInterval(refresh, 3000);
})();
</script>
</body>
</html>"""


def _read_json(path: Path) -> dict | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def _age_seconds(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        delta = (datetime.now(timezone.utc) - stamp).total_seconds()
        return int(delta) if 0 <= delta < 86400 * 365 else None
    except ValueError:
        return None


def _safe_pr(value: object) -> str | None:
    if (isinstance(value, str) and value.startswith(PR_PREFIX)
            and re.fullmatch(re.escape(PR_PREFIX) + r"[0-9]{1,10}", value)):
        return value
    return None


def snapshot() -> dict:
    """Return a bounded public-for-local-use representation of the ledger."""
    ledger = _read_json(LEDGER) or {}
    heart = _read_json(HEARTBEAT) or {}
    tasks = ledger.get("tasks")
    tasks = tasks if isinstance(tasks, dict) else {}
    rows = []
    for level in range(4, 21):
        record = tasks.get(str(level))
        record = record if isinstance(record, dict) else {}
        status = record.get("status", "PENDING")
        status = status if status in VALID_STATUS else "PENDING"
        name = record.get("name")
        name = name[:150] if isinstance(name, str) else "Level " + str(level)
        attempts = record.get("attempts")
        attempts = attempts if type(attempts) is int and 0 <= attempts <= 2 else 0
        blocker = record.get("blocker")
        blocker = blocker if isinstance(blocker, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", blocker) else None
        rows.append({
            "level": level, "name": name, "status": status, "attempts": attempts,
            "blocker": blocker, "pr": _safe_pr(record.get("draft_pr")),
        })
    # Only verified draft PR links count as completed engineering artifacts.
    drafts = sum(x["status"] == "DRAFT_PR_CREATED" and x["pr"] is not None for x in rows)
    blocked = sum(x["status"] == "BLOCKED" for x in rows)
    pending = sum(x["status"] == "PENDING" for x in rows)
    running = next((x["level"] for x in rows if x["status"] == "RUNNING"), None)
    age = _age_seconds(heart.get("updated_utc"))
    mode = heart.get("mode") if isinstance(heart.get("mode"), str) else "NO_HEARTBEAT"
    live = bool(ledger and age is not None and age <= 35
                and mode in ("RUNNING", "WORKING") and LOCK.is_file()
                and not STOP.exists())
    if not ledger:
        state, label = "NOT_INSTALLED", "NO LOCAL LEDGER"
    elif STOP.exists():
        state, label = "STOP_REQUESTED", "STOP REQUESTED"
    elif live:
        state, label = "LIVE", "WORKER LIVE"
    elif drafts + blocked == TOTAL and running is None:
        state, label = "QUEUE_ENDED", "DRAFT QUEUE FINISHED"
    else:
        state, label = "NOT_VERIFIED", "WORKER NOT VERIFIED LIVE"
    return {
        "worker": {"state": state, "label": label, "mode": mode, "age_seconds": age},
        "totals": {"drafts": drafts, "blocked": blocked, "pending": pending,
                   "running": running, "total": TOTAL},
        "stages": rows, "last_activity": ledger.get("updated_utc") if ledger else None,
        "scientific_levels_verified": 0, "automatic_merge": False, "production_deploy": False,
    }


def make_handler(token: str, port: int):
    allowed_hosts = {"127.0.0.1:" + str(port), "localhost:" + str(port)}
    class Handler(BaseHTTPRequestHandler):
        def _host_ok(self) -> bool:
            return self.headers.get("Host", "").lower() in allowed_hosts

        def _send(self, code: int, data: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'nonce-" + token +
                             "'; style-src 'unsafe-inline'; connect-src 'self'; "
                             "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if not self._host_ok():
                self._send(403, b"Forbidden", "text/plain")
            elif self.path == "/":
                page = PAGE.replace("__TOKEN__", token)
                self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/status":
                payload = json.dumps(snapshot(), ensure_ascii=True).encode("utf-8")
                self._send(200, payload, "application/json; charset=utf-8")
            else:
                self._send(404, b"Not found", "text/plain")

        def do_POST(self) -> None:
            if not self._host_ok() or self.path != "/api/stop":
                self._send(403, b"Forbidden", "text/plain")
                return
            origin = self.headers.get("Origin")
            if origin and origin not in ("http://127.0.0.1:" + str(port),
                                         "http://localhost:" + str(port)):
                self._send(403, b"Forbidden", "text/plain")
                return
            if not secrets.compare_digest(self.headers.get("X-PDUFA-Dashboard-Token", ""), token):
                self._send(403, b"Forbidden", "text/plain")
                return
            try:
                HOME.mkdir(parents=True, exist_ok=True)
                if STOP.is_symlink():
                    raise OSError("Unsafe stop token")
                # Worker checks this file between bounded tasks. The dashboard
                # deliberately does not kill any process or start a new worker.
                with STOP.open("x", encoding="utf-8") as handle:
                    handle.write("OWNER REQUESTED VIA LOCAL DASHBOARD\n")
            except FileExistsError:
                pass
            except OSError:
                self._send(500, b"Unable to create stop request", "text/plain")
                return
            self._send(202, b'{"stop_requested":true}', "application/json")

        def log_message(self, fmt: str, *args: object) -> None:
            # No auth/token logging. Only local debugging without request headers.
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open the local dashboard in your browser")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    token = secrets.token_urlsafe(32)
    url = "http://" + HOST + ":" + str(args.port) + "/"
    server = ThreadingHTTPServer((HOST, args.port), make_handler(token, args.port))
    print("PDUFA LIVE CODING DASHBOARD:", url, flush=True)
    print("Reads local progress only. Close with Ctrl+C; the worker is unaffected.", flush=True)
    if args.open:
        threading.Timer(0.35, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\nDashboard viewing stopped; coding worker unaffected.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
