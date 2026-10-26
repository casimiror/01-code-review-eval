"""Tiny notes server: serves the .txt notes in a directory over HTTP.

uv run python demo/notes_server.py --dir demo/notes --port 8000
curl localhost:8000/notes            # list notes
curl localhost:8000/notes/todo.txt   # read one
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

NOTES_DIR = Path("notes")


def list_notes() -> list[str]:
    return sorted(p.name for p in NOTES_DIR.glob("*.txt"))


class NotesHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/notes":
            self._send(200, json.dumps(list_notes()).encode(), "application/json")
        elif self.path.startswith("/notes/"):
            name = self.path.removeprefix("/notes/")
            # Only serve files that the listing exposes.
            if name not in list_notes():
                self._send(404, b"note not found\n", "text/plain")
                return
            self._send(200, (NOTES_DIR / name).read_bytes(), "text/plain; charset=utf-8")
        else:
            self._send(404, b"not found\n", "text/plain")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    global NOTES_DIR
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", type=Path, default=NOTES_DIR)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    NOTES_DIR = args.dir
    print(f"serving {NOTES_DIR} on http://localhost:{args.port}/notes")
    ThreadingHTTPServer(("127.0.0.1", args.port), NotesHandler).serve_forever()


if __name__ == "__main__":
    main()
