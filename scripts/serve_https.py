#!/usr/bin/env python3
import argparse
import functools
import http.server
import ssl


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        if self.path.rstrip("/").endswith((".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".woff", ".woff2")):
            self.send_header("Cache-Control", "public, max-age=30, must-revalidate")
        else:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()


class ThreadingHTTPSServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, server_address, handler, context):
        self.ssl_context = context
        super().__init__(server_address, handler)

    def get_request(self):
        sock, address = self.socket.accept()
        sock.settimeout(10)
        return self.ssl_context.wrap_socket(sock, server_side=True), address


def main():
    parser = argparse.ArgumentParser(description="Serve a directory over HTTPS")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--dir", dest="directory", required=True)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    handler = functools.partial(NoCacheHTTPRequestHandler, directory=args.directory)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=args.cert, keyfile=args.key)
    httpd = ThreadingHTTPSServer((args.host, args.port), handler, ctx)

    print(f"HTTPS serving {args.directory} on https://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
