"""Preview the site on your network, including GitHub Pages' extensionless HTML paths."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.resolve_alias()
        super().do_GET()

    def do_HEAD(self):
        self.resolve_alias()
        super().do_HEAD()

    def resolve_alias(self):
        requested = urlsplit(self.path)
        target = Path(self.translate_path(requested.path))
        if not target.exists() and not target.suffix and target.with_suffix(".html").is_file():
            self.path = urlunsplit(requested._replace(path=requested.path + ".html"))

    def send_error(self, code, message=None, explain=None):
        not_found = Path(self.directory) / "404.html"
        if code != 404 or not not_found.exists():
            return super().send_error(code, message, explain)
        content = not_found.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Directory to preview (default: repository root)")
    parser.add_argument("--host", default="0.0.0.0", help="Listening address (default: all interfaces)")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    directory = args.root.resolve()
    if not (directory / "index.html").is_file():
        parser.error("No index.html found. Build the site before previewing it.")
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(directory)))
    print(f"Local preview: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        addresses = sorted(set(socket.gethostbyname_ex(socket.gethostname())[2]))
    except socket.gaierror:
        addresses = []
    for address in addresses:
        if args.host == "0.0.0.0" and not address.startswith("127."):
            print(f"Network preview: http://{address}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
