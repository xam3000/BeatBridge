"""Loopback preview of the institute player with its private data directory."""

import argparse
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import StudyApp


class PreviewServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}/hoertest/"
    with make_server("127.0.0.1", args.port, StudyApp(args.data, url),
                     server_class=PreviewServer, handler_class=QuietHandler) as server:
        print(url, flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
