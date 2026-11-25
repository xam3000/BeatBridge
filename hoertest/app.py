"""Small WSGI application mounted under the institute's protected study URL."""

from functools import lru_cache
import hashlib
import hmac
from html import escape
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
import json
import os
from pathlib import Path
import re
import secrets
from string import Template
import time
from urllib.parse import parse_qs, urlsplit

from .session import Session, WEB_VERSION, file_sha256, read, web_protocol


HERE = Path(__file__).resolve().parent


def checked_inventory(root):
    key = read(root / "study_key.json")
    if key.get("version") != WEB_VERSION or key.get("procedure_sha256") != file_sha256(web_protocol(key)):
        raise ValueError("Bitte das Institutspaket mit der passenden Protokollfassung vorbereiten.")
    if not (root / "responses.sqlite").is_file():
        raise ValueError("Die vorbereitete Sitzungsdatenbank fehlt.")
    seen = set()
    for assets in [key["practice"], *key["panels"].values()]:
        for asset in assets:
            sha = asset["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", sha) or asset["path"] != f"media/{sha}.wav":
                raise ValueError("Ungültiger Medienverweis im privaten Institutspaket.")
            path = (root / asset["path"]).resolve()
            if not path.is_relative_to(root) or (sha not in seen and file_sha256(path) != sha):
                raise ValueError(f"Geprüfter Ausschnitt fehlt oder wurde verändert: {sha}")
            seen.add(sha)
    return key


def wav_slice(path, start, length):
    with path.open("rb") as audio:
        audio.seek(start)
        while length:
            chunk = audio.read(min(65536, length))
            if not chunk:
                break
            yield chunk
            length -= len(chunk)


def audio_response(path, environ, reply):
    size = path.stat().st_size
    start, end, status = 0, size - 1, 200
    headers = [("Accept-Ranges", "bytes")]
    requested = environ.get("HTTP_RANGE")
    if requested:
        match = re.fullmatch(r"bytes=(\d{0,19})-(\d{0,19})", requested)
        if match and any(match.groups()):
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(end, int(last)) if last else end
            else:
                start = max(0, size - int(last))
        else:
            start = size
        if start > end:
            return reply(416, headers=[("Content-Range", f"bytes */{size}")])
        status = 206
        headers.append(("Content-Range", f"bytes {start}-{end}/{size}"))
    length = end - start + 1
    return reply(status, wav_slice(path, start, length), "audio/wav", headers, length)


class StudyApp:
    def __init__(self, root, public_url, contact=""):
        url = urlsplit(public_url)
        local = url.hostname in ("127.0.0.1", "localhost", "::1")
        if (not url.netloc or url.username is not None or url.password is not None or url.query or url.fragment
                or not (url.scheme == "https" or (local and url.scheme == "http"))
                or not re.fullmatch(r"(?:/[a-zA-Z0-9_-]+)*/?", url.path)):
            raise ValueError("Eine HTTPS-Adresse der Studie angeben (für lokale Proben auch HTTP auf localhost).")
        self.root = Path(root).resolve()
        self.key = checked_inventory(self.root)
        self.secret = bytes.fromhex(self.key["seed"])
        self.origin = f"{url.scheme}://{url.netloc}"
        self.host = url.netloc.lower()
        self.prefix = url.path.rstrip("/") + "/"
        self.secure = "; Secure" if url.scheme == "https" else ""
        self.start = Template((HERE / "start.html").read_text(encoding="utf-8"))
        self.player = (HERE / "player.html").read_bytes()
        self.contact = escape(contact)
        self.session = lru_cache(maxsize=64)(self._session)

    def _session(self, code):
        return Session(self.root, code, verified_key=self.key, create=False)

    def sign(self, purpose, value):
        return hmac.new(self.secret, f"{purpose}:{value}".encode("ascii"), hashlib.sha256).hexdigest()

    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"]

        def reply(status, body=b"", mime="text/plain; charset=utf-8", headers=(), length=None):
            if isinstance(body, str):
                body = body.encode("utf-8")
            if length is None:
                length = len(body)
            start_response(f"{status} {HTTPStatus(status).phrase}", [
                ("Content-Type", mime), ("Content-Length", str(length)), ("Cache-Control", "private, no-store"),
                ("Referrer-Policy", "strict-origin"), ("X-Content-Type-Options", "nosniff"),
                ("X-Robots-Tag", "noindex, nofollow"), ("X-Frame-Options", "DENY"),
                ("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline'; "
                 "style-src 'self' 'unsafe-inline'; media-src 'self'; connect-src 'self'; "
                 "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"), *headers])
            if method == "HEAD":
                return []
            return [body] if isinstance(body, bytes) else body

        def json_reply(status, obj):
            return reply(status, json.dumps(obj), "application/json; charset=utf-8")

        def cookie(name, value, path):
            return ("Set-Cookie", f"{name}={value}; Path={path}; Max-Age=604800; HttpOnly; SameSite=Lax{self.secure}")

        if environ.get("HTTP_HOST", "").lower() != self.host:
            return reply(404)
        path = environ.get("SCRIPT_NAME", "") + environ["PATH_INFO"]
        if path == self.prefix.rstrip("/") and method in ("GET", "HEAD"):
            return reply(308, headers=[("Location", self.prefix)])
        if not path.startswith(self.prefix):
            return reply(404)
        route = path[len(self.prefix):]
        if method == "POST" and environ.get("HTTP_ORIGIN") != self.origin:
            return reply(403)
        cookies = SimpleCookie()
        try:
            cookies.load(environ.get("HTTP_COOKIE", ""))
        except CookieError:
            return reply(400)
        if route == "" and method in ("GET", "HEAD"):
            # A preview bot or page reload uses no counterbalancing seat.
            code = secrets.token_hex(8)
            nonce = f"{code}.{int(time.time())}"
            resume = ""
            previous = cookies.get("bb_last")
            if previous:
                old, _, signature = previous.value.partition(".")
                if (re.fullmatch("[0-9a-f]{16}", old) and signature.isascii()
                        and secrets.compare_digest(self.sign("last", old), signature)):
                    try:
                        if not self.session(old).state()["done"]:
                            resume = f'<p><a href="s/{old}/">Begonnene Sitzung fortsetzen</a></p>'
                    except KeyError:
                        pass  # Cookie retained after restoring a database backup.
            count = len(self.key["panels"])
            scope = ("Nach zwei Übungsclips hören Sie sieben Songpaare." if self.key["split"] == "final" else
                     f"Dieser Probelauf umfasst zwei Übungsclips und {count} Entwicklungspaar{'e' if count != 1 else ''}.")
            duration = "Planen Sie rund 30–40 Minuten ein. " if self.key["split"] == "final" else ""
            html = self.start.substitute(nonce=nonce + "." + self.sign("start", nonce), resume=resume, scope=scope,
                                         duration=duration,
                                         contact=f"<p>Kontakt: {self.contact}</p>" if self.contact else "")
            return reply(200, html, "text/html; charset=utf-8")
        if route == "start" and method == "POST":
            if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/x-www-form-urlencoded":
                return reply(415)
            try:
                fields = parse_qs(read_body(environ).decode("ascii"), max_num_fields=4)
                nonce, signature = fields["form"][0].rsplit(".", 1)
                code, stamp = nonce.split(".")
                if (not re.fullmatch("[0-9a-f]{16}", code) or not re.fullmatch(r"\d{1,12}", stamp)
                        or not 0 <= time.time() - int(stamp) <= 7200
                        or not signature.isascii() or not secrets.compare_digest(self.sign("start", nonce), signature)
                        or fields.get("participate") != ["yes"]):
                    raise ValueError
            except (ValueError, KeyError, UnicodeError):
                return reply(400, "Bitte die Startseite neu öffnen und die Teilnahme bestätigen.")
            try:
                Session(self.root, code, verified_key=self.key)
            except ValueError as exc:
                return reply(503, str(exc))
            location = self.prefix + "s/" + code + "/"
            return reply(303, headers=[("Location", location), cookie("bb_access", self.sign("access", code), location),
                                       cookie("bb_last", code + "." + self.sign("last", code), self.prefix)])
        match = re.fullmatch(r"s/([0-9a-f]{16})/(.*)", route)
        if not match:
            return reply(404)
        code, resource = match.groups()
        access = cookies.get("bb_access")
        if not access or not access.value.isascii() or not secrets.compare_digest(access.value, self.sign("access", code)):
            return reply(403, "Diese Sitzung gehört zu dem Browser, in dem sie gestartet wurde.")
        try:
            session = self.session(code)
        except KeyError:
            return reply(404, "Diese Sitzung ist nicht mehr verfügbar.")
        if method in ("GET", "HEAD"):
            if resource == "":
                return reply(200, self.player, "text/html; charset=utf-8")
            state = session.state()
            if resource == "state":
                return json_reply(200, state)
            clip = resource.removeprefix("audio/")
            if resource.startswith("audio/") and not state["done"] and clip in state["codes"]:
                return audio_response(self.root / session.mapping[clip]["path"], environ, reply)
        if method == "POST" and resource == "event":
            if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
                return reply(415)
            try:
                event = json.loads(read_body(environ))
                if not isinstance(event, dict):
                    raise ValueError("Ungültige Eingabe.")
                session.event(event)
            except (TypeError, ValueError):
                return json_reply(400, {"error": "Eingabe nicht gespeichert. Bitte Seite neu laden und erneut versuchen."})
            return json_reply(200, session.state())
        return reply(404)


def read_body(environ):
    size = int(environ.get("CONTENT_LENGTH") or 0)
    if not 0 < size <= 32768:
        raise ValueError("Ungültige Anfragegröße.")
    return environ["wsgi.input"].read(size)


def create_app():
    return StudyApp(os.environ["BEATBRIDGE_STUDY_DATA"], os.environ["BEATBRIDGE_STUDY_URL"],
                    os.environ.get("BEATBRIDGE_STUDY_CONTACT", ""))
