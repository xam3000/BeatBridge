"""Run one blinded listening session on the operator's local computer."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import shutil

from src.evaluation.p11_session import Session, prepare, seal


def server_for(session, port):
    prefix = "/" + secrets.token_urlsafe(24)
    html = Path(__file__).with_name("p11_web.html").read_bytes()

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
                with path.open("rb") as stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(path.stat().st_size))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    try:
                        shutil.copyfileobj(stream, self.wfile)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass  # A listener started a different clip.
            else:
                self.send_error(404)

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (self.route() != "event" or self.headers.get("Origin") != origin
                    or self.headers.get_content_type() != "application/json"):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2048:
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
    serve = commands.add_parser("serve")
    serve.add_argument("root", type=Path)
    serve.add_argument("person", help="Pseudonym, e.g. VP01")
    serve.add_argument("--port", type=int, default=0)
    export = commands.add_parser("seal")
    export.add_argument("root", type=Path)
    export.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.panels, args.practice, args.split)
    elif args.command == "seal":
        seal(args.root, args.output)
    else:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", args.person):
            parser.error("Use a short pseudonymous ID")
        server, url = server_for(Session(args.root, args.person), args.port)
        print(url, flush=True)
        with server:
            server.serve_forever()


if __name__ == "__main__":
    main()
