# Autorstwo i zasoby zewnętrzne

Interfejs bazuje na szablonie Namari dostosowanym do strony Koła Fantastyki i Gier UW.
Poniżej wymieniono wykorzystane biblioteki i zasoby zewnętrzne.

| Zasób | Autorstwo i źródło |
| --- | --- |
| Namari Landing Page 1.1.0 | ShapingRain; dostosowany szablon, informacje w `static/css/style.css` i `namari-color.css` |
| jQuery 3.7.1 | OpenJS Foundation, MIT, https://jquery.com/license/ |
| Featherlight 1.3.3 i galeria | Noël Raoul Bossart, MIT; zachowane nagłówki źródeł |
| Load Awesome 1.1.0 | Daniel Cardoso, MIT; wyodrębniony CSS z zachowanym nagłówkiem |
| Animate.css | Dan Eden; informacje o autorstwie/licencji w pliku źródłowym |
| Pozostałe dodatki JS | WOW, enllax, scrollUp, easing, stickyNavbar, Waypoints, imagesLoaded i lightbox; informacje w nagłówkach plików w `static/js` |
| Tailwind CSS | Narzędzie do budowania CSS; wersje zależności w `package-lock.json` |
| Fonty, ikony, mapa | Google Fonts, Font Awesome, Google Maps; ładowane z usług zewnętrznych |
| Zdjęcia, logo, regulaminy | Materiały strony Koła Fantastyki i Gier UW |

Dodatek stickyNavbar dostosowano do jQuery 3, poprawiając selektor atrybutu
oraz zastępując `load(handler)` wywołaniem `on('load', ...)`.

Biblioteki i materiały zewnętrzne zachowują własne warunki licencyjne.
