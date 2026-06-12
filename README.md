# generator.py

A simple Python crawler that visits a target domain, collects all URL paths from links and JavaScript files, and extracts the path segments as a wordlist — ready to use with tools like `ffuf`, `gobuster`, or `feroxbuster`.

```
target.com/dev          →  dev
target.com/api/v1       →  api, v1
target.com/user-profile →  user, profile
/static/js/app.bundle   →  static, app, bundle   (from JS paths)
```

> ⚠️ For authorized security testing, bug bounty recon, and CTF challenges only. Only use against systems you own or have explicit permission to test.

---

## How It Works

1. Starts at the target homepage
2. Follows every internal link (`href`, `src`, `action`, `data-url`, …)
3. Fetches `.js` files and scans them for quoted path strings
4. Splits each URL path on `/` `-` `_` `.` and strips extensions
5. Writes all unique segments to a `.txt` wordlist

---

## Installation

```bash
git clone https://github.com/yourusername/generator.git
cd generator
pip install requests beautifulsoup4
```

Python 3.10+ required. No other dependencies.

---

## Usage

```bash
python generator.py -t target.com
```

```
Options:
  -t, --target     Target domain  (required)
  --depth          Crawl depth: 1 ≈ 20 pages | 2 ≈ 60 | 3 ≈ 150   (default: 1)
  -o, --output     Output file  (default: wordlist.txt)
  --show-paths     Print every discovered path at the end
  -q, --quiet      Suppress per-page output
  --timeout        Request timeout in seconds  (default: 8)
```

---

## Examples

```bash
# Quick run — homepage only
python generator.py -t target.com

# Deeper crawl, custom output
python generator.py -t target.com --depth 2 -o target_words.txt

# Full crawl + see all paths discovered
python generator.py -t target.com --depth 3 --show-paths

# Silent mode
python generator.py -t target.com -q -o wordlist.txt
```

---

## Example Output

Running against a typical web app:

```
  target  →  target.com
  depth   →  2
  output  →  wordlist.txt

  [  1] https://target.com
  [  2] https://target.com/about
  [  3] https://target.com/api/v1/docs
  [  4] https://target.com/login
  ...

  pages crawled  :  47
  words found    :  183
  saved          →  wordlist.txt
```

`wordlist.txt`:
```
about
admin
api
auth
dashboard
dev
docs
internal
login
logout
panel
profile
reset
settings
static
upload
users
v1
...
```

---

## Use With

```bash
# Directory fuzzing
ffuf -w wordlist.txt -u https://target.com/FUZZ

# Gobuster
gobuster dir -u https://target.com -w wordlist.txt

# Feroxbuster
feroxbuster --url https://target.com --wordlist wordlist.txt
```

---
