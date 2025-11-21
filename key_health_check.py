#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, os, random, sys, time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from google import genai
from google.genai import errors as genai_errors

MIN_DELAY = 1.0
MAX_DELAY = 3.0
ERROR_COOLDOWN = (30.0, 35.0)
RATE_LIMIT_COOLDOWN = 60.0
DEFAULT_MODEL = "gemini-2.5-flash"

PING_PROMPT = (
    "ROLE: System health checker.\n"
    "GOAL: Respond with a short acknowledgement string.\n"
    "OUTPUT: Return a JSON object {\"ok\": true}."
)

@dataclass(slots=True)
class KeyStatus:
    key: str
    ok: bool
    reason: str

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Aistudio/Gemini API keys.")
    parser.add_argument("--key-file", required=True, type=Path, help="Path to file containing API keys (one per line)")
    parser.add_argument("--out-good", required=True, type=Path, help="Destination file for usable keys")
    parser.add_argument("--max-keys", type=int, default=None, help="Optional cap on number of keys to test")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model ID to ping")
    return parser.parse_args()

def load_keys(path: Path) -> List[str]:
    if not path.exists():
        sys.exit(f"❌ Key file not found: {path}")
    keys = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]
    if not keys:
        sys.exit("❌ No keys found after filtering blanks/comments.")
    return keys

def build_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)

def is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    if "429" in msg or "resource_exhausted" in msg or "limit exceeded" in msg:
        return True
    if isinstance(err, (genai_errors.APIError, genai_errors.ServerError)):
        code = getattr(err, "status_code", None) or getattr(err, "code", None)
        if code == 429:
            return True
    return False

def is_auth_error(err: Exception) -> bool:
    msg = str(err).lower()
    if "401" in msg or "403" in msg or "unauth" in msg or "permission" in msg:
        return True
    if isinstance(err, genai_errors.ClientError):
        code = getattr(err, "status_code", None) or getattr(err, "code", None)
        if code in (401, 403):
            return True
    return False

def ping_key(api_key: str, model: str) -> Tuple[bool, str]:
    client = build_client(api_key)
    try:
        client.models.generate_content(
            model=model,
            contents=[PING_PROMPT, "Respond now."]
        )
        return True, "ok"
    except Exception as err:
        if is_auth_error(err):
            return False, "unauthorized"
        if is_rate_limit(err):
            return False, "rate_limited"
        print(f"⚠️ {api_key[:8]}… failed ({err}).")
        return False, "error"

def write_good_keys(path: Path, keys: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")

def main() -> None:
    args = parse_args()
    keys = load_keys(args.key_file)
    if args.max_keys:
        keys = keys[:args.max_keys]
    good: List[str] = []
    statuses: List[KeyStatus] = []

    for idx, key in enumerate(keys, start=1):
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        ok, reason = ping_key(key, args.model)
        statuses.append(KeyStatus(key, ok, reason))
        marker = "AVAILABLE" if ok else "UNAVAILABLE"
        print(f"[{idx:04d}/{len(keys):04d}] {key[:8]}… → {marker} ({reason})")
        if ok:
            good.append(key)

    write_good_keys(args.out_good, good)
    ok_count = sum(1 for s in statuses if s.ok)
    fail_count = len(statuses) - ok_count
    unauth_count = sum(1 for s in statuses if s.reason == "unauthorized")
    print(f"\nSummary: {ok_count} usable | {fail_count} failed | {unauth_count} unauthorized.")
    print(f"✅ Good keys saved to: {args.out_good}")

if __name__ == "__main__":
    main()
