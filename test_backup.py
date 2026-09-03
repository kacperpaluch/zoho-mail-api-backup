"""python3 test_backup.py"""
import os, tempfile, zipfile
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ.update(ZOHO_CLIENT_ID="x", ZOHO_CLIENT_SECRET="x", ZOHO_REFRESH_TOKEN="x", BACKUP_DIR=tmp)
import backup

# nazwa pliku: deterministyczna i bezpieczna
n = backup.name_for({"messageId": "17098", "subject": "Faktura 12/2026: zapłać!", "receivedTime": "1772000000000"})
assert n.endswith("_17098.eml") and "/" not in n and " " not in n, n
assert backup.name_for({"messageId": "1", "subject": None, "receivedTime": "0"}).count("no-subject") == 1
assert backup.name_for({"messageId": "1", "subject": "a" * 300, "receivedTime": "0"}).count("a") == 80

# zip = stan na teraz: skasowany ze skrzynki mail zostaje w archiwum, ale nie wchodzi do zipa
(backup.MAIL / "Inbox").mkdir(parents=True)
for f in ("2026-01-01_jest_1.eml", "2025-01-01_skasowany_2.eml"):
    (backup.MAIL / "Inbox" / f).write_text("From: a@b\n\nbody")
backup.snapshot({Path("Inbox/2026-01-01_jest_1.eml")})
[z] = list(backup.ZIPS.glob("*.zip"))
assert zipfile.ZipFile(z).namelist() == ["Inbox/2026-01-01_jest_1.eml"], zipfile.ZipFile(z).namelist()
assert (backup.MAIL / "Inbox/2025-01-01_skasowany_2.eml").exists(), "archiwum nigdy nie kasuje"
# cron: niedziela 23:30
from datetime import datetime
niedz, pon = datetime(2026, 9, 6, 23, 30), datetime(2026, 9, 7, 23, 30)
assert backup.cron_due("30 23 * * 0", niedz)
assert not backup.cron_due("30 23 * * 0", pon)
assert not backup.cron_due("30 23 * * 0", datetime(2026, 9, 6, 23, 31))
assert backup.cron_due("30 23 * * 7", niedz), "7 to tez niedziela"
assert backup.cron_due("0 3 * * *", datetime(2026, 9, 7, 3, 0)), "codziennie 3:00"
assert backup.cron_due("*/15 * * * *", datetime(2026, 9, 7, 3, 45)), "co 15 minut"
assert not backup.cron_due("*/15 * * * *", datetime(2026, 9, 7, 3, 46))
assert backup.cron_due("0 2 1 * *", datetime(2026, 9, 1, 2, 0)), "1. dnia miesiaca"
assert backup.cron_due("30 23 * * 1-5", datetime(2026, 9, 9, 23, 30)), "sroda w zakresie"
assert not backup.cron_due("30 23 * * 1-5", niedz)
assert backup.cron_due("30 23 * * 0,3", datetime(2026, 9, 9, 23, 30)), "lista dni"
assert backup.cron_due("30 23 * * 1-7", niedz), "zakres 1-7 obejmuje niedziele"
assert backup.cron_due("30 23 * * 1-7", pon), "zakres 1-7 obejmuje poniedzialek"
assert not backup.cron_due("30 23 * * 1-5", niedz), "1-5 to nie niedziela"

# glob na nieistniejacym katalogu nie wybucha (start bez data/zips)
import shutil; shutil.rmtree(backup.ZIPS)
assert not any(backup.ZIPS.glob("*.zip"))

print("ok", n)
