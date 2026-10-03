"""One-command runner for the GSI local authoring server.

Discovers the local LAN IP, loads or generates a persistent auth token from .env,
prints phone-ready connection URLs, and starts the server bound to 0.0.0.0.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def get_lan_ip() -> str:
    """Detect the machine's primary local network IP address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connecting to a public non-routable address finds the outbound interface without sending packets
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()


def get_or_create_auth_token(override: str = "") -> str:
    """Retrieve token from env/override, or persist a clean token in .env."""
    if override.strip():
        return override.strip()

    env_val = os.environ.get("GSI_LOCAL_AUTH_TOKEN", "").strip()
    if env_val:
        return env_val

    if ENV_FILE.is_file():
        text = ENV_FILE.read_text(encoding="utf-8")
        match = re.search(r"^GSI_LOCAL_AUTH_TOKEN\s*=\s*[\"']?([^\"'\r\n]+)", text, re.MULTILINE)
        if match and match.group(1).strip():
            return match.group(1).strip()

    # Generate a friendly, secure token
    new_token = f"gsi-author-{secrets.token_hex(4)}"
    with open(ENV_FILE, "a", encoding="utf-8") as f:
        f.write(f"\nGSI_LOCAL_AUTH_TOKEN={new_token}\n")
    return new_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Start GSI authoring server for desktop and mobile.")
    parser.add_argument("--port", type=int, default=8021, help="Port to listen on (default: 8021)")
    parser.add_argument("--token", default="", help="Optional token override")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0 for LAN)")
    args = parser.parse_args()

    lan_ip = get_lan_ip()
    token = get_or_create_auth_token(args.token)
    port = args.port

    local_url = f"http://127.0.0.1:{port}/__local/editor/"
    phone_url = f"http://{lan_ip}:{port}/__local/editor/?token={token}"

    box_width = 72
    print("=" * box_width)
    print("  GENOME STABILITY INDUCERS — LOCAL AUTHORING SERVER".center(box_width))
    print("=" * box_width)
    print(f"  Network Host:  {args.host}:{port}")
    print(f"  Auth Token:    {token}")
    print("-" * box_width)
    print("  Desktop:")
    print(f"    {local_url}")
    print("  Phone / LAN (open once on your phone to authenticate):")
    print(f"    {phone_url}")
    print("-" * box_width)
    print("  Tip: Bookmark the Phone URL on your phone's home screen.")
    print("       Future visits will stay authorized via local cookie.")
    print("=" * box_width)
    print("  Press Ctrl+C to stop the server.\n")

    os.environ["GSI_LOCAL_AUTH_TOKEN"] = token
    os.environ["GSI_BIND_HOST"] = args.host

    from tools.submission_server import SubmissionHandler, ThreadingHTTPServer

    server = ThreadingHTTPServer((args.host, port), SubmissionHandler)
    server.gsi_auth_token = token
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down authoring server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
