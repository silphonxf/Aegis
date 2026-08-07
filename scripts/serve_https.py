#!/usr/bin/env python3
import argparse
import functools
import http.client
import http.server
import json
import ssl
from urllib.parse import urlsplit


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, directory=None, proxy_prefix=None, proxy_target=None, **kwargs):
        self.proxy_prefix = (proxy_prefix or "").rstrip("/")
        self.proxy_target = urlsplit(proxy_target) if proxy_target else None
        super().__init__(*args, directory=directory, **kwargs)

    def _is_proxy_request(self):
        return bool(
            self.proxy_prefix
            and self.proxy_target
            and (self.path == self.proxy_prefix or self.path.startswith(f"{self.proxy_prefix}/"))
        )

    def _proxy_request(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if content_length > 2 * 1024 * 1024:
            self.send_error(413, "Request body too large")
            return

        body = self.rfile.read(content_length) if content_length else None
        target = self.proxy_target
        connection_class = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        connection_kwargs = {"host": target.hostname, "port": target.port, "timeout": 30}
        if target.scheme == "https":
            # The proxy target is the fixed loopback Aegis backend. External TLS
            # terminates on this 18791 listener; never use this context remotely.
            connection_kwargs["context"] = ssl._create_unverified_context()
        connection = connection_class(**connection_kwargs)
        forward_headers = {}
        for name in (
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-OpenClaw-Channel",
            "X-Feishu-Open-Id",
            "X-OpenClaw-Session-Key",
            "X-OpenClaw-Account-Id",
        ):
            value = self.headers.get(name)
            if value:
                forward_headers[name] = value
        forward_headers["X-Aegis-Proxy-Client-IP"] = self.client_address[0]
        if body is not None:
            forward_headers["Content-Length"] = str(len(body))

        try:
            connection.request(self.command, self.path, body=body, headers=forward_headers)
            upstream = connection.getresponse()
            response_body = upstream.read()
            self.send_response(upstream.status, upstream.reason)
            for name in ("Content-Type", "X-Request-ID", "WWW-Authenticate"):
                value = upstream.getheader(name)
                if value:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_body)
        except (OSError, http.client.HTTPException) as exc:
            payload = json.dumps(
                {"code": "AEGIS_BACKEND_UNAVAILABLE", "message": str(exc)},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        finally:
            connection.close()

    def do_GET(self):
        if self._is_proxy_request():
            self._proxy_request()
            return
        super().do_GET()

    def do_HEAD(self):
        if self._is_proxy_request():
            self._proxy_request()
            return
        super().do_HEAD()

    def do_POST(self):
        if self._is_proxy_request():
            self._proxy_request()
            return
        self.send_error(405, "Method Not Allowed")

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
    parser.add_argument("--proxy-prefix")
    parser.add_argument("--proxy-target")
    args = parser.parse_args()

    if bool(args.proxy_prefix) != bool(args.proxy_target):
        parser.error("--proxy-prefix and --proxy-target must be provided together")
    handler = functools.partial(
        NoCacheHTTPRequestHandler,
        directory=args.directory,
        proxy_prefix=args.proxy_prefix,
        proxy_target=args.proxy_target,
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=args.cert, keyfile=args.key)
    httpd = ThreadingHTTPSServer((args.host, args.port), handler, ctx)

    print(f"HTTPS serving {args.directory} on https://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
