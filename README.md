# Koło Fantastyki i Gier UW

Strona Koła Fantastyki i Gier Uniwersytetu Warszawskiego z informacjami o wydarzeniach i systemem bezpłatnych biletów. Uczestnik pobiera PDF z kodem QR, który obsługa sprawdza po zalogowaniu.

![Strona główna z przykładowym wydarzeniem](docs/screenshots/home.png)

## Funkcje

- Prezentacja koła, galeria zdjęć i regulaminy.
- Zarządzanie wydarzeniami w panelu Django i odliczanie do ich rozpoczęcia.
- Generowanie biletów PDF z kodem QR oraz weryfikacja przez obsługę.
- Formularz kontaktowy z walidacją danych i limitem wysyłek.

## Technologie

Python 3.13+ · Django 5.2 · PostgreSQL 17 · Docker Compose · Gunicorn · Nginx · Tailwind CSS · ReportLab · qrcode

## Jak działają bilety

Bilet otrzymuje losowy identyfikator i kod QR prowadzący do strony weryfikacji. Zalogowany pracownik sprawdza status i zatwierdza pierwsze użycie. Od tego momentu bilet jest ważny przez 48 godzin; ponowne zatwierdzenie nie przedłuża jego ważności.

Generowanie PDF i zapis biletu odbywają się w jednej transakcji. Jeśli tworzenie dokumentu się nie powiedzie, zapis zostaje wycofany. Blokady PostgreSQL chronią limit pobrań i pierwsze zatwierdzenie przy równoczesnych żądaniach. Logika znajduje się w [website/services.py](website/services.py).

Limit wynosi 2 bilety na adres IP w ciągu 30 dni — osoby korzystające ze wspólnej sieci współdzielą ten limit.

## Uruchomienie lokalne

Wymagania: Docker z Compose v2 oraz Python 3.13+ do utworzenia konfiguracji.

```bash
git clone https://github.com/Lysden97/KoloFantastyki.git
cd KoloFantastyki
python scripts/setup_env.py
docker compose up --build -d --wait
docker compose exec django-web python manage.py seed_demo
docker compose exec django-web python manage.py createsuperuser
```

Na Windows można użyć `py` zamiast `python`. Skrypt tworzy `.env` z lokalną konfiguracją i losowymi sekretami. Dostępne ustawienia opisuje [.env.example](.env.example).

Strona działa pod http://localhost:8001/, a panel administratora pod http://localhost:8001/k9xV7rB2pQzL/.

Polecenie `seed_demo` dodaje przykładowe wydarzenie. Migracje i budowanie plików statycznych wykonują się automatycznie. W lokalnej konfiguracji wiadomości z formularza kontaktowego są wypisywane w logach aplikacji.

Aby sprawdzić cały proces, pobierz bilet ze strony głównej, zaloguj się do panelu utworzonym kontem i otwórz adres z kodu QR.

Zatrzymanie aplikacji z zachowaniem danych:

```bash
docker compose down
```

## Testy

Po uruchomieniu kontenerów:

```bash
docker compose exec -e TEST_POSTGRES=True django-web python manage.py test --settings=djangoKoloFantastyki.test_settings
```

Testy obejmują generowanie PDF, uprawnienia, ważność biletów, formularz kontaktowy i limity przy równoczesnych żądaniach. Korzystają z osobnej bazy testowej PostgreSQL.

## Interfejs

Strona wykorzystuje dostosowany szablon **Namari**. Autorzy bibliotek i informacje o zasobach są wymienieni w [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
