#!/usr/bin/env python3
"""Zoho Mail -> .eml, przyrostowo. Raz na X dni zip snapshot katalogu."""
import json, os, re, time, urllib.error, urllib.parse, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

DC        = os.environ.get("ZOHO_DC", "eu")            # eu | com | in | com.au | jp
CID       = os.environ["ZOHO_CLIENT_ID"]
SECRET    = os.environ["ZOHO_CLIENT_SECRET"]
REFRESH   = os.environ["ZOHO_REFRESH_TOKEN"]
OUT       = Path(os.environ.get("BACKUP_DIR", "/data"))
GAP       = float(os.environ.get("REQ_INTERVAL", "2.1"))          # limit 30 req/min
SYNC_EVERY = float(os.environ.get("SYNC_INTERVAL_HOURS", "6")) * 3600
ZIP_CRON   = os.environ.get("ZIP_CRON", "30 23 * * 0")            # niedziela 23:30
MAIL, ZIPS = OUT / "mail", OUT / "zips"
_tok, _last_req = ["", 0.0], [0.0]

def _field(spec, val, hi):
    for part in spec.split(","):
        part, _, step = part.partition("/")
        lo, _, up = part.partition("-")
        lo, up = (0, hi) if part == "*" else (int(lo), int(up or lo))
        if lo <= val <= up and (val - lo) % int(step or 1) == 0:
            return True
    return False

def cron_due(expr, t):
    """Podzbior crona: 'min godz dzien miesiac dzien_tygodnia', 0 = niedziela.
    Obsluguje liczby, listy (1,5), zakresy (1-5), kroki (*/15) i '*'."""
    m, h, dom, mon, dow = expr.split()
    return (_field(m, t.minute, 59) and _field(h, t.hour, 23) and _field(dom, t.day, 31)
            and _field(mon, t.month, 12) and _field(dow.replace("7", "0"), (t.weekday() + 1) % 7, 6))

def log(*a): print(datetime.now().strftime("%F %T"), *a, flush=True)

def token():
    if time.time() < _tok[1]:
        return _tok[0]
    q = urllib.parse.urlencode({"refresh_token": REFRESH, "client_id": CID,
                                "client_secret": SECRET, "grant_type": "refresh_token"})
    r = json.load(urllib.request.urlopen(
        f"https://accounts.zoho.{DC}/oauth/v2/token?{q}", data=b"", timeout=60))
    if "access_token" not in r:
        raise SystemExit(f"OAuth failed: {r}")
    _tok[:] = [r["access_token"], time.time() + r.get("expires_in", 3600) - 60]
    return _tok[0]

def api(path, **params):
    url = f"https://mail.zoho.{DC}/api{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        # tempo liczone od startu poprzedniego requestu, nie sztywny sen przed kazdym:
        # inaczej czas trwania requestu doklada sie do odstepu i realny rate spada
        time.sleep(max(0, GAP - (time.time() - _last_req[0])))
        _last_req[0] = time.time()
        req = urllib.request.Request(url, headers={"Authorization": f"Zoho-oauthtoken {token()}"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=120)).get("data")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError(f"HTTP {e.code} na {path}") from None
            wait = 60 * (attempt + 1)
            log(f"HTTP {e.code}, czekam {wait}s")
            time.sleep(wait)

def name_for(msg):
    """Deterministyczna nazwa pliku - istnienie pliku = mail juz pobrany."""
    day = datetime.fromtimestamp(int(msg.get("receivedTime", 0)) / 1000).strftime("%Y-%m-%d")
    subj = re.sub(r"[^\w\s.-]", "", msg.get("subject") or "no-subject").strip()[:80] or "no-subject"
    subj = re.sub(r"\s+", "_", subj)
    return f"{day}_{subj}_{msg['messageId']}.eml"

def sync():
    """Dociaga brakujace maile. Zwraca zbior sciezek obecnych TERAZ w skrzynce."""
    acc = api("/accounts")[0]
    aid = acc["accountId"]
    log(f"konto {acc.get('primaryEmailAddress', aid)}")
    new, current = 0, set()
    for f in api(f"/accounts/{aid}/folders"):
        fid, fdir = f["folderId"], MAIL / re.sub(r"[/\\]", "_", f["folderName"])
        fdir.mkdir(parents=True, exist_ok=True)
        log(f"folder {f['folderName']}: na dysku {len(list(fdir.glob('*.eml')))} .eml")
        start = 1
        while True:
            msgs = api(f"/accounts/{aid}/messages/view", folderId=fid, start=start, limit=200) or []
            current.update(fdir.relative_to(MAIL) / name_for(m) for m in msgs)
            todo = [m for m in msgs if not (fdir / name_for(m)).exists()]
            for m in todo:
                d = api(f"/accounts/{aid}/messages/{m['messageId']}/originalmessage")
                (fdir / name_for(m)).write_text(d["content"], encoding="utf-8")
                new += 1
                if new % 50 == 0:     # pierwszy przebieg trwa godzinami, pokaz ze zyje
                    log(f"  pobrano {new}, teraz {f['folderName']} (strona od {start})")
            if len(msgs) < 200:   # listing lecimy zawsze do konca: przerwany
                break             # pierwszy przebieg inaczej zostawilby dziure
            start += 200
        log(f"  {f['folderName']}: gotowe, {len(list(fdir.glob('*.eml')))} plikow")
    log(f"nowych maili: {new}, w skrzynce teraz: {len(current)}")
    return current

def snapshot(current):
    """Zip = stan skrzynki na teraz: tylko maile, ktore nadal w niej sa."""
    ZIPS.mkdir(parents=True, exist_ok=True)
    dst = ZIPS / f"zoho-{datetime.now():%Y-%m-%d}.zip"
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(current):
            z.write(MAIL / rel, rel)
    kept, total = len(current), len(list(MAIL.rglob("*.eml")))
    log(f"zip: {dst.name} - {kept} maili ({dst.stat().st_size / 1e6:.0f} MB), "
        f"archiwum trzyma {total}")

if __name__ == "__main__":
    log(f"start: sync co {SYNC_EVERY / 3600:g}h, zip wg crona '{ZIP_CRON}' ({time.tzname[0]})")
    last_sync = 0.0
    while True:
        due = cron_due(ZIP_CRON, datetime.now())
        if due or time.time() - last_sync >= SYNC_EVERY:
            last_sync = time.time()
            try:
                current = sync()
                if due or not any(ZIPS.glob("*.zip")):   # zawsze jeden zip na dzien dobry
                    snapshot(current)                    # zip tylko po udanym listingu
            except Exception as e:                       # petla ma przezyc kazdy blad sieci
                log("BLAD:", repr(e))
        if os.environ.get("RUN_ONCE"):
            break
        time.sleep(60 - datetime.now().second)           # budzik co pelna minute
