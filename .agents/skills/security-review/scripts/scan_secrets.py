#!/usr/bin/env python3
"""Deterministik secret tarayıcı — sızmış kimlik bilgisini merge kapısına çevirir.

Verilen dosya veya dizinde yaygın secret desenlerini (API key, private key,
token, hardcoded parola, .env sızıntısı) regex ile tarar. Bulguyu
dosya:satır + kural adı ile raporlar. Bulgu varsa exit 1; temizse exit 0.

Kullanım:
  python3 scan_secrets.py <dosya|dizin> [<dosya|dizin> ...]
  python3 scan_secrets.py src/ config/app.py

Bağımlılıksız (yalnız stdlib). Yanlış-pozitifi azaltmak için örnek/placeholder
değerler (xx: your_key, example, changeme, <...>) elenir; yine de bir kanıt
sinyalidir, insan teyidi gerekir.
"""
import fnmatch
import os
import re
import sys

# Taranmayacak yollar (gürültü ve kendi kaynağımız).
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__",
             "dist", "build", ".mypy_cache", ".pytest_cache"}
# İkili/irrelevant uzantılar.
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip",
            ".gz", ".tar", ".woff", ".woff2", ".ttf", ".mp4", ".lock"}
MAX_BYTES = 2_000_000  # >2MB dosyayı atla (üretilmiş/ikili olasılığı)

# Placeholder / örnek işaretçileri: bunları içeren değer bulgu sayılmaz.
PLACEHOLDER = re.compile(
    r"(your[_-]?|example|sample|placeholder|changeme|dummy|redacted|"
    r"xxxx+|\.\.\.|<[^>]+>|\{\{|\$\{|test[_-]?key|fake)", re.I)

# Her kural: (ad, regex). regex bir "değer" grubu içerebilir (grup 1) ya da
# tamamı imza olabilir. Değer grubu varsa placeholder elemesi ona uygulanır.
RULES = [
    ("AWS Access Key ID",
     re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("AWS Secret Access Key",
     re.compile(r"(?i)aws.{0,20}?(?:secret|key).{0,3}['\"]([A-Za-z0-9/+=]{40})['\"]")),
    ("Private key blok",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub token",
     re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,255})\b")),
    ("Slack token",
     re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("Google API key",
     re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b")),
    ("Stripe secret key",
     re.compile(r"\b((?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,})\b")),
    ("OpenAI/Anthropic key",
     re.compile(r"\b(sk-(?:ant-)?[A-Za-z0-9_\-]{20,})\b")),
    ("JWT",
     re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}\b")),
    ("Generic API key/token atama",
     re.compile(r"(?i)(?:api[_-]?key|secret|token|access[_-]?key|auth)"
                r"\s*[:=]\s*['\"]([A-Za-z0-9_\-/+=]{16,})['\"]")),
    ("Hardcoded parola",
     re.compile(r"(?i)(?:password|passwd|pwd|db[_-]?pass)"
                r"\s*[:=]\s*['\"]([^'\"\s]{6,})['\"]")),
    ("Bağlantı dizesinde parola",
     re.compile(r"(?i)(?:postgres|mysql|mongodb|redis|amqp)(?:ql)?://"
                r"[^:/\s]+:([^@/\s]{4,})@")),
]


def is_placeholder(text):
    return bool(PLACEHOLDER.search(text))


def scan_line(line):
    """Bir satırda bulunan (kural, eşleşme) listesini döndür."""
    hits = []
    for name, rx in RULES:
        for m in rx.finditer(line):
            value = m.group(1) if m.groups() else m.group(0)
            if value and is_placeholder(value):
                continue
            hits.append((name, value))
    return hits


def is_excluded(path, patterns):
    """Yol dışlama glob'larından birine uyuyor mu (normalize edilmiş '/' ile)."""
    norm = os.path.normpath(path).replace(os.sep, "/").lstrip("./")
    return any(fnmatch.fnmatch(norm, g) or fnmatch.fnmatch("./" + norm, g)
               for g in patterns)


def iter_files(paths, exclude=()):
    for p in paths:
        if os.path.isfile(p):
            if not is_excluded(p, exclude):
                yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if os.path.splitext(f)[1].lower() in SKIP_EXT:
                        continue
                    tam = os.path.join(root, f)
                    if is_excluded(tam, exclude):
                        continue
                    yield tam
        else:
            print(f"UYARI: yol bulunamadı: {p}", file=sys.stderr)


def scan(paths, exclude=()):
    findings = []
    for path in iter_files(paths, exclude):
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    for name, value in scan_line(line):
                        preview = value if len(value) <= 12 else value[:6] + "…" + value[-3:]
                        findings.append((path, i, name, preview))
        except (OSError, UnicodeError):
            continue
    return findings


def main(argv):
    # --exclude GLOB (tekrarlanabilir): kasıtlı fixture'ları dışarıda tutar.
    # Dışlama gate KONFİGÜNDE görünür olsun diye tarayıcıya gömülmez —
    # neyin taranmadığı gizli kalmamalı.
    exclude, paths = [], []
    i = 1
    while i < len(argv):
        if argv[i] == "--exclude" and i + 1 < len(argv):
            exclude.append(argv[i + 1])
            i += 2
            continue
        paths.append(argv[i])
        i += 1
    if not paths:
        print("kullanım: scan_secrets.py [--exclude GLOB] <dosya|dizin> [...]",
              file=sys.stderr)
        return 2
    findings = scan(paths, exclude)
    if not findings:
        print("scan_secrets: temiz — secret deseni bulunamadı ✓")
        return 0
    print(f"scan_secrets: {len(findings)} olası secret bulundu ✗")
    for path, line, name, preview in findings:
        print(f"  {path}:{line}  [{name}]  → {preview}")
    print("SONUÇ: FAIL — secret'ı kaldır, geçmişten temizle, anahtarı döndür (rotate).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
