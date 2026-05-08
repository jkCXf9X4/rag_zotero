#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from huggingface_hub import set_client_factory, snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a Sentence Transformers model locally")
    parser.add_argument(
        "model_id",
        nargs="?",
        default="sentence-transformers/all-mpnet-base-v2",
        help="Hugging Face model id to download",
    )
    parser.add_argument(
        "target_dir",
        nargs="?",
        default=None,
        help="Directory to download into (default: ./models/<model_id>)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification for the Hugging Face download",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = Path(
        args.target_dir or f"./models/{args.model_id.replace('/', '__')}"
    ).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    if args.insecure:
        set_client_factory(lambda: httpx.Client(verify=False))
    elif ssl_cert := os.getenv("SSL_CERT_FILE"):
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ssl_cert)
        os.environ.setdefault("CURL_CA_BUNDLE", ssl_cert)

    snapshot_download(repo_id=args.model_id, local_dir=target_dir)
    print(str(target_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
