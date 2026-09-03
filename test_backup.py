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
print("ok", n)
