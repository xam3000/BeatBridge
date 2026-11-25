"""Run one blinded listening session on the operator's local computer."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets

from src.evaluation.p11_session import VERSION, Session, prepare, prepare_run02, read, seal
import hoertest
from hoertest.app import audio_response


def server_for(session, port):
    prefix = "/" + secrets.token_urlsafe(24)
    html = Path(hoertest.__file__).with_name("player.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, data, mime):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def json(self, status, obj):
            self.reply(status, json.dumps(obj).encode(), "application/json")

        def route(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return None
            if self.path.startswith(prefix + "/"):
                return self.path[len(prefix) + 1:]
            return None

        def do_GET(self):
            route = self.route()
            if route == "":
                self.reply(200, html, "text/html; charset=utf-8")
            elif route == "state":
                self.json(200, session.state())
            elif route and route.startswith("audio/"):
                code = route[6:]
                state = session.state()
                if state["done"] or code not in state["codes"]:
                    self.send_error(404)
                    return
                path = Path(session.mapping[code]["path"])
                def send_audio(status, body=b"", mime="text/plain; charset=utf-8", headers=(), length=None):
                    self.send_response(status)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(body) if length is None else length))
                    self.send_header("Cache-Control", "no-store")
                    for name, value in headers:
                        self.send_header(name, value)
                    self.end_headers()
                    if self.command == "HEAD":
                        return
                    try:
                        for chunk in ([body] if isinstance(body, bytes) else body):
                            self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass  # A listener started a different clip.
                audio_response(path, {"HTTP_RANGE": self.headers.get("Range", "")}, send_audio)
            else:
                self.send_error(404)

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (self.route() != "event" or self.headers.get("Origin") != origin
                    or self.headers.get_content_type() != "application/json"):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32768:
                    raise ValueError("Ungültige Anfragegröße.")
                event = json.loads(self.rfile.read(size))
                if not isinstance(event, dict):
                    raise ValueError("Ungültige Eingabe.")
                session.event(event)
            except (ValueError, TypeError):
                self.json(400, dict(error="Eingabe nicht gespeichert. Bitte Seite neu laden und erneut versuchen."))
                return
            self.json(200, session.state())

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, f"http://127.0.0.1:{server.server_port}{prefix}/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("prepare")
    init.add_argument("root", type=Path)
    init.add_argument("--panels", nargs="+", type=Path, required=True)
    init.add_argument("--practice", type=Path, required=True)
    init.add_argument("--split", choices=["development", "final"], required=True)
    init.add_argument("--institute", action="store_true", help="Prepare a portable private directory for the institute site")
    init.add_argument("--fixed-rule-anchors", action="store_true",
                      help="Present the same 49 recordings to everyone, with a hard cut at each rule cue")
    run02 = commands.add_parser("prepare-run02", help="Package the 49 verified Run02 recordings for the institute")
    run02.add_argument("root", type=Path)
    run02.add_argument("--source", type=Path, required=True)
    run02.add_argument("--practice", type=Path, required=True)
    windows = commands.add_parser("prepare-windows", help="Add neutral transition windows to an existing package without changing audio, key or sessions")
    windows.add_argument("root", type=Path)
    windows.add_argument("--panels", nargs="+", type=Path, required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("root", type=Path)
    serve.add_argument("person", help="Pseudonym, e.g. VP01")
    serve.add_argument("--port", type=int, default=0)
    export = commands.add_parser("seal")
    export.add_argument("root", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--deadline", help="Prespecified submission deadline in ISO 8601 with UTC offset.")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.panels, args.practice, args.split, institute=args.institute,
                fixed_rule_anchors=args.fixed_rule_anchors)
    elif args.command == "prepare-run02":
        prepare_run02(args.root, args.source, args.practice)
    elif args.command == "prepare-windows":
        from src.evaluation.p11_windows import prepare_windows
        print(prepare_windows(args.root, args.panels))
    elif args.command == "seal":
        seal(args.root, args.output, deadline=args.deadline)
    else:
        if read(args.root / "study_key.json")["version"] != VERSION:
            parser.error("Für ein Institutspaket bitte python -m hoertest DATENORDNER verwenden.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", args.person):
            parser.error("Use a short pseudonymous ID")
        server, url = server_for(Session(args.root, args.person), args.port)
        print(url, flush=True)
        with server:
            server.serve_forever()


if __name__ == "__main__":
    main()
