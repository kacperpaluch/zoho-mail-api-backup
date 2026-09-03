# zoho-mail-api-backup

[![Docker Hub](https://img.shields.io/docker/pulls/kpa90/zoho-mail-api-backup?logo=docker)](https://hub.docker.com/r/kpa90/zoho-mail-api-backup)

Przyrostowy backup Zoho Mail do `.eml` + pelny zip skrzynki co X dni.
Czysty Python stdlib, zero zaleznosci, obraz ~50 MB.

## Uruchomienie

Obraz dostepny na [Docker Hub](https://hub.docker.com/r/kpa90/zoho-mail-api-backup).

Wpisz dane z api-console.zoho.eu (Self Client) w `environment:` w `docker-compose.yml`, potem:

```bash
docker compose up -d
```

Pierwszy przebieg sciaga cala skrzynke (limit Zoho to 30 req/min, wiec ~7000 maili = ok. 4 h),
kolejne dociagaja tylko nowe.

## Konfiguracja

Wszystko siedzi w `environment:` w `docker-compose.yml`:

| zmienna | domyslnie | znaczenie |
|---|---|---|
| `SYNC_INTERVAL_HOURS` | 6 | co ile godzin sprawdzac nowe maile |
| `ZIP_CRON` | `30 23 * * 0` | kiedy robic zip - skladnia crona, niedziela 23:30 |
| `TZ` | UTC | strefa czasowa, wedlug ktorej liczy sie `ZIP_CRON` |
| `REQ_INTERVAL` | 2.1 | sekundy miedzy requestami: `60 / REQ_INTERVAL` = req/min |
| `RUN_ONCE` | - | ustaw `1` = jeden przebieg i wyjscie (do crona hosta) |

`ZIP_CRON` to zwykly cron (`min godz dzien miesiac dzien_tygodnia`, 0 = niedziela):
`30 23 * * 0` niedziela 23:30, `0 3 * * *` codziennie o 3:00, `0 2 1 * *` 1. dnia miesiaca.
Pamietaj o `TZ`, inaczej godzina liczy sie wg UTC.

`REQ_INTERVAL` to odstep miedzy requestami w sekundach, czyli `60 / REQ_INTERVAL` requestow
na minute: `2.1` to ~28/min (tuz pod limitem Zoho), `3` to 20/min, `6` to 10/min.

Uwaga: klucze siedza w `docker-compose.yml`, wiec nie commituj go z wypelnionymi wartosciami.
Jesli kiedys bedziesz chcial - przenies je do `docker-compose.override.yml` (Compose dociaga go
sam, jest w .gitignore).

## Wynik

```
data/mail/Inbox/2026-09-03_Faktura_1709887058769100001.eml
data/zips/zoho-2026-09-03.zip
```

`.eml` importuje sie do Apple Mail, Thunderbirda itd. Zalaczniki siedza w MIME.

- `data/mail/` rosnie przyrostowo i **nic z niego nie znika** - skasowany w Zoho mail zostaje.
- `data/zips/` to snapshoty "stan na teraz": w zipie jest dokladnie to, co w danym dniu bylo
  w skrzynce, bez skasowanych.

## Jak dziala dedup

Nazwa pliku jest deterministyczna (data + temat + messageId), wiec istnienie pliku = mail juz
pobrany. Zadnej bazy ani pliku stanu. Skasujesz plik - pobierze go ponownie.
Zip pakuje lokalny mirror, wiec nie kosztuje ani jednego requestu do Zoho.

## Rozwoj

```bash
docker compose -f docker-compose.build.yml up -d --build
python3 test_backup.py
```
