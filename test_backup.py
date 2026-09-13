"""python3 test_backup.py"""
import os, tempfile, zipfile
import io, json
from pathlib import Path
from unittest.mock import patch

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

# blad zapisu ZIP-a nie niszczy poprzedniej kopii i nie zostawia pliku tymczasowego
old_zip = z.read_bytes()
with patch.object(zipfile.ZipFile, "write", side_effect=OSError("dysk pelny")):
    try:
        backup.snapshot({Path("Inbox/2026-01-01_jest_1.eml")})
    except OSError:
        pass
    else:
        raise AssertionError("blad ZIP-a musi przerwac zapis")
assert z.read_bytes() == old_zip
assert not list(backup.ZIPS.glob("*.tmp"))

# przerwany zapis maila nie zostawia pliku, ktory dedup uzna za kompletny
msg = {"messageId": "2", "subject": "test", "receivedTime": "0"}
responses = [[{"accountId": "1"}], [{"folderId": "1", "folderName": "Inbox"}], [msg], {"content": "From: a@b\n\nbody"}]
dst = backup.MAIL / "Inbox" / backup.name_for(msg)
def interrupted_write(path, *args, **kwargs):
    with path.open("w") as f:
        f.write("partial")
    raise OSError("dysk pelny")

with patch.object(backup, "api", side_effect=responses), patch.object(Path, "write_text", interrupted_write):
    try:
        backup.sync()
    except OSError:
        pass
    else:
        raise AssertionError("blad maila musi przerwac zapis")
assert not dst.exists()
assert not list(dst.parent.glob("*.tmp"))
with patch.object(backup, "api", side_effect=responses):
    assert dst.relative_to(backup.MAIL) in backup.sync()
assert dst.read_text() == responses[-1]["content"]

# tylko jawna lista jest listingiem; brak/null/zly typ data to blad
with patch.object(backup, "token", return_value="x"), patch.object(backup.time, "sleep"):
    for payload in ({}, {"data": None}, {"data": {}}, {"data": ""}, []):
        with patch.object(backup.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            try:
                backup.api("/accounts/1/messages/view")
            except RuntimeError:
                pass
            else:
                raise AssertionError(f"zaakceptowano bledna odpowiedz: {payload}")
    with patch.object(backup.urllib.request, "urlopen", return_value=io.BytesIO(b'{"data": []}')):
        assert backup.api("/accounts/1/messages/view") == []
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
