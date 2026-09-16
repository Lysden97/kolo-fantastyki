# Wdrożenie i aktualizacja

Dostarczony Compose jest przeznaczony do lokalnego uruchomienia na 127.0.0.1:8001.
Kontenery używają Gunicorna, ale proxy nie ma skonfigurowanego certyfikatu TLS.

## Przed wdrożeniem

1. Wykonaj kopię bazy i zweryfikuj możliwość odtworzenia.
2. Wygeneruj nowe sekrety; historyczne hasło i SECRET_KEY traktuj jako ujawnione.
3. Ustaw DEBUG=False, ALLOWED_HOSTS na właściwą domenę i CSRF_TRUSTED_ORIGINS na jej origin https://.
4. Skonfiguruj TLS w Nginx, certyfikaty montowane tylko do odczytu i przekierowanie portu 80 na 443.
5. Zachowaj nadpisywanie X-Forwarded-For i X-Forwarded-Proto. Port Gunicorna ma być osiągalny tylko przez zaufany proxy.
6. Ustaw backend SMTP, nadawcę należącego do obsługiwanej domeny oraz CONTACT_RECIPIENT.
7. Uruchom migracje na kopii bazy, następnie testy i kontrole wdrożenia.

```bash
python manage.py check --deploy --fail-level WARNING
```

HSTS obejmuje tylko daną domenę; includeSubDomains/preload nie są włączane automatycznie.
Polecenie może zwrócić ostrzeżenia o tych opcjach — decyzję podejmuje administrator
po sprawdzeniu wszystkich subdomen i warunków preload. Nie wyciszaj ich bez przeglądu.

Jeżeli TLS kończy się na innym proxy przed Nginx, potrzebna jest osobna, świadomie
skonfigurowana granica zaufania. Obecny Nginx nadpisuje protokół wartością własnego
połączenia i nie należy bezwarunkowo przekazywać nagłówków od klienta.

## Migracja z wcześniejszej wersji

- Nie usuwaj wolumenu postgres_data; jego usunięcie oznacza utratę bazy.
- Zachowaj dotychczasową nazwę bazy i użytkownika w DATABASE_NAME i DATABASE_USER.
- Zmień hasło także w PostgreSQL, nie tylko w .env.
- Migracja 0006 rozszerza identyfikator biletu bez zmiany wartości istniejących biletów,
  dodaje logi kontaktu i indeksy.
- Stare ośmioznakowe linki QR i dotychczasowy adres panelu pozostają dostępne.
- Dane statyczne są teraz zapisywane w osobnym wolumenie staticfiles.
- Sprawdź chronologię istniejących wydarzeń; walidacja dat obejmuje nowe edycje
  formularzy, nie modyfikuje samoczynnie historycznych rekordów.

## Utrzymanie

Compose uruchamia osobną usługę cleanup: czyszczenie po starcie oraz co 24 godziny.
Alternatywnie scheduler hosta może wykonywać raz dziennie:

```bash
python manage.py clean_old_ticket_logs
```

Logi IP biletów są usuwane po 30 dniach, kontaktu po 1 dniu (z dokładnością harmonogramu).
Bilety nie są usuwane przez to polecenie. Formularz ma limit 3 prób na godzinę,
również gdy SMTP jest niedostępne. Nie zapisuje treści wiadomości w bazie.

Utrzymuj kopie bazy, aktualizuj przypięte zależności, monitoruj logi i działanie cleanup.
Nowe obrazy kontenerów oraz migracje przetestuj przed zmianą działającego wdrożenia.
