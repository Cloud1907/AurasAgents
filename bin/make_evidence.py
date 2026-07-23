#!/usr/bin/env python3
"""evidence.json üretir — CI'da veya lokalde koşar.

Kullanım:
  python3 bin/make_evidence.py --out evidence.json \
    --contract "#12" --task-class code-change \
    --check "tests=passed" --check "lint=passed" \
    --digest "test-report=path/to/report.xml"

CI'da GITHUB_SHA / GITHUB_RUN_ID ortam değişkenlerini otomatik kullanır.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def git_sha() -> str:
    env = os.environ.get("GITHUB_SHA")
    if env:
        return env
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "0" * 40


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def parse_kv(pairs, what):
    out = []
    for p in pairs or []:
        if "=" not in p:
            sys.exit(f"HATA: {what} 'ad=değer' biçiminde olmalı: {p!r}")
        k, v = p.split("=", 1)
        out.append((k.strip(), v.strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--contract", default="micro")
    ap.add_argument("--task-class", default="micro")
    ap.add_argument("--engine", default="claude-code")
    ap.add_argument("--model", default=os.environ.get("AURAS_MODEL", ""))
    ap.add_argument("--skill", action="append", default=[])
    ap.add_argument("--check", action="append", default=[],
                    help="ad=passed|failed|skipped")
    ap.add_argument("--digest", action="append", default=[],
                    help="ad=dosya_yolu (sha256 hesaplanır)")
    ap.add_argument("--risk-provisional", default=None,
                    choices=["auto", "approval", "deny"])
    ap.add_argument("--risk-final", default=None,
                    choices=["auto", "approval", "deny"])
    args = ap.parse_args()

    checks = []
    run_url = ""
    if os.environ.get("GITHUB_RUN_ID"):
        run_url = (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
            f"{os.environ['GITHUB_RUN_ID']}"
        )
    for name, status in parse_kv(args.check, "--check"):
        if status not in ("passed", "failed", "skipped"):
            sys.exit(f"HATA: geçersiz check durumu: {name}={status}")
        item = {"name": name, "status": status}
        if run_url:
            item["run_url"] = run_url
        checks.append(item)
    if not checks:
        sys.exit("HATA: en az bir --check gerekli")

    digests = {}
    for name, path in parse_kv(args.digest, "--digest"):
        if not os.path.isfile(path):
            sys.exit(f"HATA: digest dosyası yok: {path}")
        digests[name] = sha256_file(path)

    evidence = {
        "schema_version": 1,
        "contract_id": args.contract,
        "commit_sha": git_sha(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_class": args.task_class,
        "engine": {
            "name": args.engine,
            "model": args.model,
            "skills_used": args.skill,
        },
        "checks": checks,
    }
    if digests:
        evidence["digests"] = digests
    if args.risk_provisional or args.risk_final:
        evidence["risk"] = {}
        if args.risk_provisional:
            evidence["risk"]["provisional"] = args.risk_provisional
        if args.risk_final:
            evidence["risk"]["final"] = args.risk_final

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    print(f"evidence yazıldı: {args.out} "
          f"({len(checks)} check, {len(digests)} digest)")
    failed = [c["name"] for c in checks if c["status"] == "failed"]
    if failed:
        print(f"UYARI: başarısız check'ler: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
