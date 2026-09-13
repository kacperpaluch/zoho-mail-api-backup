# zoho-mail-api-backup

Automatyczny backup skrzynki Zoho Mail przez oficjalne API. Czysty Python stdlib,
zero zaleznosci, obraz ~50 MB.

## Dwa rodzaje backupu

**Archiwum przyrostowe** (`data/mail/`) — kazdy mail jako plik `.eml`, uporzadkowany
w foldery jak w skrzynce. Nic nie jest z niego kasowane: mail usuniety w Zoho zostaje
na dysku na zawsze.

**Snapshot cykliczny** (`data/zips/`) — zip z mailami znalezionymi podczas ostatniego
udanego przebiegu, o porze
ustawionej cronem (domyslnie w niedziele o 23:30).
To nie jest stan z jednej chwili: podczas pobierania poczta moze przychodzic,
znikac lub zmieniac foldery. Maili nieobecnych w listingu nie dodajemy do zipa.
Pakuje lokalny mirror, wiec nie kosztuje ani jednego dodatkowego requestu.
Maile i ZIP-y sa zapisywane atomowo przez pliki tymczasowe. Nieprawidlowa
odpowiedz API przerywa przebieg zamiast udawac pusty folder.

## Uruchomienie

```yaml
services:
  zoho-backup:
    image: kpa90/zoho-mail-api-backup:latest
    container_name: zoho-backup
    restart: unless-stopped
    environment:
      ZOHO_CLIENT_ID: ""
      ZOHO_CLIENT_SECRET: ""
      ZOHO_REFRESH_TOKEN: ""
      ZOHO_DC: eu
      TZ: Europe/Warsaw
      SYNC_INTERVAL_HOURS: 6
      ZIP_CRON: "30 23 * * 0"
      REQ_INTERVAL: 2.1
    volumes:
      - ./data:/data
```

Dane OAuth wygenerujesz w api-console.zoho.eu (Self Client), scope tylko do odczytu:
`ZohoMail.messages.READ,ZohoMail.folders.READ,ZohoMail.accounts.READ`.

## Zmienne

| zmienna | domyslnie | znaczenie |
|---|---|---|
| `ZOHO_DC` | `eu` | region konta: eu, com, in, com.au, jp |
| `SYNC_INTERVAL_HOURS` | 6 | co ile godzin dociagac nowe maile |
| `ZIP_CRON` | `30 23 * * 0` | kiedy snapshot — skladnia crona (0 = niedziela) |
| `TZ` | UTC | strefa czasowa dla `ZIP_CRON` |
| `REQ_INTERVAL` | 2.1 | sekundy miedzy requestami: `60 / REQ_INTERVAL` = req/min |
| `RUN_ONCE` | — | `1` = jeden przebieg i wyjscie (do crona) |

Pierwszy przebieg sciaga cala skrzynke i od razu robi pierwszy zip. Limit Zoho to
30 requestow na minute, wiec 7000 maili zajmuje okolo 4 godzin. Kolejne przebiegi
dociagaja tylko nowe wiadomosci.

Dedup opiera sie na nazwie pliku (data + temat + messageId) — zadnej bazy ani pliku
stanu. Restart kontenera niczego nie powtarza.

Zrodla: https://github.com/kacperpaluch/zoho-mail-api-backup
