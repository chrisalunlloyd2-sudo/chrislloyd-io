#!/usr/bin/env python3
"""Daily, deterministic mirror of the Shopify store onto this site. No LLM, no hand-picked list.

  python3 scripts/sync_store.py            one sync now (fetch feed, rebuild, test, commit, push if changed)
  python3 scripts/sync_store.py --dry-run  rebuild + test but do not commit or push
  python3 scripts/sync_store.py --force    allow the product count to drop by more than half
  python3 scripts/sync_store.py --daily    stay running; sync once per Edmonton day after 06:00

Safety: refuses to touch anything when the feed is empty or collapses below half of the
current product count, when the tests fail (generated files are restored), or when the
generated paths already have uncommitted changes.
Log: $LIFE_HOME (default /root/.life)/store-sync.log; last success: store-sync-last.txt
"""
import json, os, random, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.environ.get("LIFE_HOME", "/root/.life")
LOG = os.path.join(HOME, "store-sync.log")
STAMP = os.path.join(HOME, "store-sync-last.txt")
GENERATED = ["data/store.json", "products.html", "assets/store", "data/i18n"]
MAX_WAIT = 40 * 60

def log(msg):
    line = datetime.now(ZoneInfo("America/Edmonton")).strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    try:
        os.makedirs(HOME, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    except OSError: pass

def run(args, check=True):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {(r.stdout + r.stderr).strip()[-600:]}")
    return r

def fetch_feed(base):
    products, page, waited = [], 1, 0
    while True:
        url = f"{base}/products.json?limit=250&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (chrislloyd-io store sync)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                got = json.load(r)["products"]
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise RuntimeError(f"feed HTTP {e.code}")
            pause = random.randint(90, 150)
            if waited + pause > MAX_WAIT:
                raise RuntimeError("feed still rate limited (HTTP 429) after 40 minutes")
            log(f"feed HTTP 429, retrying in {pause}s")
            time.sleep(pause); waited += pause
            continue
        products += got
        if len(got) < 250:
            return products
        page += 1

def prune_images():
    store = json.load(open(os.path.join(ROOT, "data/store.json"), encoding="utf-8"))
    keep = {os.path.basename(i["image"]) for i in store["items"] if i.get("image")}
    other = ""
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "store", "node_modules")]
        for fn in files:
            if fn.endswith((".html", ".js", ".css")) or (fn.endswith(".json") and fn != "store.json"):
                other += open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
    removed = 0
    d = os.path.join(ROOT, "assets/store")
    for fn in os.listdir(d):
        if fn not in keep and fn not in other:
            os.remove(os.path.join(d, fn)); removed += 1
    return removed

def sync(dry=False, force=False):
    dirty = run(["git", "status", "--porcelain", "--"] + GENERATED).stdout.strip()
    if dirty:
        raise RuntimeError("generated files already have uncommitted changes; not touching them:\n" + dirty[:300])
    run(["git", "pull", "--ff-only", "-q", "origin", "main"])
    cur = json.load(open(os.path.join(ROOT, "data/store-curation.json"), encoding="utf-8"))
    before = len(json.load(open(os.path.join(ROOT, "data/store.json"), encoding="utf-8"))["items"])
    feed = fetch_feed(cur["store_base"])
    if not feed:
        raise RuntimeError("feed returned 0 products; refusing to wipe the store page")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import gen_store
    rules = json.load(open(os.path.join(ROOT, "data/store-rules.json"), encoding="utf-8"))
    avail = sum(1 for p in feed if gen_store.in_stock(p) and not re.match(r"(?i)^example product", p["title"]))
    if avail == 0 or (avail < before / 2 and not force):
        raise RuntimeError(f"feed has {avail} in-stock products vs {before} on the site; refusing (use --force if real)")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"products": feed}, f)
        snap = f.name
    try:
        gen_store.main(snap)
    finally:
        os.remove(snap)
    removed = prune_images()
    todo = run([sys.executable, "scripts/i18n_extract.py", "--sync"]).stdout.strip().splitlines()
    english_only = next((l for l in todo if "without French" in l), "")
    changed = run(["git", "status", "--porcelain", "--"] + GENERATED).stdout.strip()
    if not changed:
        log(f"no change: {before} products, feed has {avail} in stock")
        return
    t = run([sys.executable, "-m", "unittest", "scripts.test_store", "scripts.test_i18n"], check=False)
    if t.returncode != 0:
        run(["git", "checkout", "--"] + GENERATED)
        run(["git", "clean", "-fdq", "--", "assets/store", "data/i18n"])
        raise RuntimeError("tests failed after rebuild; restored previous files:\n" + (t.stdout + t.stderr)[-500:])
    log(f"rebuilt: {before} -> {avail} products, {removed} old images removed; {english_only}")
    if dry:
        log("dry run: not committing")
        return
    run(["git", "add", "-A", "--"] + GENERATED)
    run(["git", "commit", "-q", "-m",
         f"Daily store sync: {avail} in-stock products\n\nAutomatic, from the Shopify products.json feed (scripts/sync_store.py)."])
    run(["git", "push", "-q", "origin", "main"])
    log("committed and pushed")

def run_once(dry=False, force=False):
    try:
        sync(dry, force)
        with open(STAMP, "w") as f: f.write(str(int(time.time())))
        return 0
    except Exception as e:
        log("FAILED: " + str(e))
        return 1

def daily():
    last = None
    while True:
        now = datetime.now(ZoneInfo("America/Edmonton"))
        if now.hour >= 6 and last != now.date():
            if run_once() == 0:
                last = now.date()
            else:
                time.sleep(3600)
                continue
        time.sleep(600)

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--daily" in a:
        daily()
    sys.exit(run_once("--dry-run" in a, "--force" in a))
