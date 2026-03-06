#!/usr/bin/env python3
import argparse
import functools
import http.server
import ssl


def main():
    parser = argparse.ArgumentParser(description="Serve a directory over HTTPS")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--dir", dest="directory", required=True)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=args.directory)
    httpd = http.server.ThreadingHTTPServer((args.host, args.port), handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=args.cert, keyfile=args.key)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print(f"HTTPS serving {args.directory} on https://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
