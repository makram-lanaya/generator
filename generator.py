#!/usr/bin/env python3
"""
generator.py — URL path wordlist generator
Crawls a target, extracts path segments from links & JS files.
For authorized security testing only.
"""

import argparse
import re
import sys
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    print("[!] Run: pip install requests beautifulsoup4")
    sys.exit(1)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PathCrawler/1.0)"}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map",
    ".css", ".pdf", ".zip", ".mp4", ".webp",
}

SKIP_WORDS = {
    "the", "and", "for", "www", "http", "https",
    "com", "html", "php", "asp", "aspx", "jsp",
}


def path_to_words(path: str) -> list[str]:
    """
    /api/v1/user-profile.php  →  ['api', 'v1', 'user', 'profile']
    """
    # strip extension
    path = re.sub(r"\.[a-zA-Z0-9]{1,5}$", "", path)
    # split on /  -  _  .
    parts = re.split(r"[/\-_\.]+", path)
    words = []
    for p in parts:
        p = p.strip().lower()
        if len(p) >= 2 and p not in SKIP_WORDS and not p.isdigit():
            words.append(p)
    return words


def js_to_words(js: str) -> list[str]:
    """Pull path-like strings from JS source code."""
    words = []
    # match quoted strings that look like paths e.g. "/api/users"
    for m in re.findall(r'["\']([/a-zA-Z0-9_\-\.]{3,80})["\']', js):
        if "/" in m:
            words.extend(path_to_words(m))
    return words


def crawl(target: str, depth: int, timeout: int, quiet: bool):
    base_url = target if target.startswith("http") else f"https://{target}"
    netloc   = urlparse(base_url).netloc

    visited:   set[str]  = set()
    queue:     list[str] = [base_url]
    wordset:   set[str]  = set()
    all_paths: list[str] = []

    max_pages = {1: 20, 2: 60, 3: 150}.get(depth, 20)
    pages = 0

    while queue and pages < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout,
                             allow_redirects=True, verify=False)
        except Exception as e:
            if not quiet:
                print(f"  [!] {url}  →  {e}")
            continue

        pages += 1
        path = urlparse(url).path

        if not quiet:
            print(f"  [{pages:>3}] {url}")

        # words from the URL path itself
        for w in path_to_words(path):
            wordset.add(w)
        if path not in ("/", ""):
            all_paths.append(path)

        ct = r.headers.get("Content-Type", "")

        # ── HTML page ──────────────────────────────────────────
        if "html" in ct:
            soup = BeautifulSoup(r.text, "html.parser")

            # every tag attribute that could hold a URL
            for tag in soup.find_all(True):
                for attr in ("href", "src", "action", "data-url", "data-href", "data-src"):
                    val = tag.get(attr, "").strip()
                    if not val:
                        continue
                    if val.startswith(("mailto:", "tel:", "#", "javascript:")):
                        continue

                    full   = urljoin(url, val)
                    parsed = urlparse(full)

                    # skip external domains
                    if parsed.netloc and parsed.netloc != netloc:
                        continue

                    p_path = parsed.path
                    ext    = (re.search(r"(\.[a-z0-9]{1,5})$", p_path, re.I) or ["",""])[1].lower()

                    # extract words from path
                    for w in path_to_words(p_path):
                        wordset.add(w)

                    # queue for crawling if HTML-likely
                    if ext not in SKIP_EXTENSIONS and full not in visited:
                        queue.append(full)

            # inline <script> blocks
            for script in soup.find_all("script"):
                if script.string:
                    for w in js_to_words(script.string):
                        wordset.add(w)

        # ── external JS file ───────────────────────────────────
        elif "javascript" in ct or url.lower().endswith(".js"):
            for w in js_to_words(r.text):
                wordset.add(w)

        time.sleep(0.2)

    return sorted(wordset), pages, all_paths


def main():
    p = argparse.ArgumentParser(
        prog="generator",
        description="Crawl a target → extract URL path segments into a wordlist.",
        epilog="""
Examples:
  python generator.py -t target.com
  python generator.py -t target.com --depth 2 -o paths.txt
  python generator.py -t target.com --depth 3 --show-paths
""")

    p.add_argument("-t", "--target",  required=True, metavar="DOMAIN",
                   help="Target domain, e.g.  target.com")
    p.add_argument("--depth",         type=int, default=1, choices=[1,2,3],
                   help="1 ≈ 20 pages  |  2 ≈ 60  |  3 ≈ 150   (default: 1)")
    p.add_argument("-o", "--output",  default="wordlist.txt",
                   help="Output file  (default: wordlist.txt)")
    p.add_argument("--show-paths",    action="store_true",
                   help="Print every discovered path at the end")
    p.add_argument("-q", "--quiet",   action="store_true",
                   help="Suppress per-page output")
    p.add_argument("--timeout",       type=int, default=8,
                   help="Request timeout in seconds  (default: 8)")

    args = p.parse_args()

    print(f"\n  target  →  {args.target}")
    print(f"  depth   →  {args.depth}")
    print(f"  output  →  {args.output}\n")

    words, pages, paths = crawl(args.target, args.depth, args.timeout, args.quiet)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(words) + "\n")

    print(f"\n  pages crawled  :  {pages}")
    print(f"  words found    :  {len(words)}")
    print(f"  saved          →  {args.output}")

    if args.show_paths:
        unique = sorted(set(paths))
        print(f"\n  discovered paths ({len(unique)}):")
        for path in unique:
            print(f"    {path}")


if __name__ == "__main__":
    main()
