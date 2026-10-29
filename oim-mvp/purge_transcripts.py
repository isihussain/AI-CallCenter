#!/usr/bin/env python3
"""Apply configured tenant transcript-retention policies once."""
import json

from backend import purge_expired_transcripts


if __name__ == "__main__":
    print(json.dumps({"ok": True, "tenants": purge_expired_transcripts()}, ensure_ascii=False))
