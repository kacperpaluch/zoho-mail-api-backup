# zoho-mail-api-backup

Automatyczny backup skrzynki Zoho Mail przez oficjalne API. Czysty Python stdlib,
zero zaleznosci, obraz ~50 MB.

## Dwa rodzaje backupu

**Archiwum przyrostowe** (`data/mail/`) — kazdy mail jako plik `.eml`, uporzadkowany
w foldery jak w skrzynce. Nic nie jest z niego kasowane: mail usuniety w Zoho zostaje
na dysku na zawsze.

**Snapshot cykliczny** (`data/zips/`) — co X dni zip ze stanem skrzynki na teraz.
W zipie jest dokladnie to, co w danym dniu bylo w Zoho, bez skasowanych.
Pakuje lokalny mirror, wiec nie kosztuje ani jednego dodatkowego requestu.

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
      SYNC_INTERVAL_HOURS: 6
      ZIP_INTERVAL_DAYS: 7
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
| `ZIP_INTERVAL_DAYS` | 7 | co ile dni snapshot skrzynki |
| `REQ_INTERVAL` | 2.1 | odstep miedzy requestami (limit Zoho: 30/min) |
| `RUN_ONCE` | — | `1` = jeden przebieg i wyjscie (do crona) |

Pierwszy przebieg sciaga cala skrzynke i od razu robi pierwszy zip. Limit Zoho to
30 requestow na minute, wiec 7000 maili zajmuje okolo 4 godzin. Kolejne przebiegi
dociagaja tylko nowe wiadomosci.

Dedup opiera sie na nazwie pliku (data + temat + messageId) — zadnej bazy ani pliku
stanu. Restart kontenera niczego nie powtarza.

Zrodla: https://github.com/kacperpaluch/zoho-mail-api-backup
