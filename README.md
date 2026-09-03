# GPU-Buchungssystem

Web-App zur Planung von GPU-Zeitfenstern für Teams. Nutzer markieren Voll- oder
Teilbelegungen sowie CPU-Zeitfenster per Drag&Drop im Wochenkalender.

## Funktionsübersicht

- **Übersicht (Startseite)**: Dashboard mit allen Servern, GPU-Ausstattung und der
  Belegung heute; Sprung direkt in den Kalender des Servers.
- **Kalender** (`/calendar`): Server-Tabs oben, darunter die Woche als kompakte
  Tagesspalten (Mo–So, 0–24 h) mit Zeit-Balken je GPU; Klick in eine freie Stunde =
  1-h-Slot, Drag über mehrere GPUs markiert das Fenster (CPU-Zeile = CPU-Zeit,
  Auto-Scroll am Rand, Touch-fähig via Pointer-Events);
  alternativ über den „Neue Buchung“-Button.
- **Buchungen**: drei Modi – Vollbelegung (`train`, exklusiv, mind. 1 h), Teilbelegung
  (`dev`, geteilt, beliebig viele Nutzer gleichzeitig) und CPU (`cpu`, Zeitfenster ohne
  GPU-Zuordnung). Mehrtageszeiträume lassen
  sich wahlweise durchgehend oder als tägliche Zeitfenster (Vorschlag 08:00–16:00) buchen;
  erster und letzter Tag werden auf den gezogenen Zeitraum gekürzt. Die täglichen Einträge
  bleiben als Serie verbunden und werden gemeinsam bearbeitet oder gelöscht.
- **Konfliktregeln**: train × train/dev → Konflikt (409); dev × dev und cpu erlaubt.
- **Projekte**: Pflicht bei jeder Buchung; anlegbar mit Mitgliedern, Owner wird automatisch
  Mitglied; Owner/Admin bearbeiten, andere 403.
- **Admin**: Nutzer-, Server-/GPU- und Projektverwaltung inkl. Kontofreigabe,
  Deaktivierung und Löschen von Konten und Projekten. Beim Löschen werden die zugehörigen
  Buchungen entfernt; Projekte eines gelöschten Nutzers gehen an den löschenden Admin über.
  GPUs mit Buchungen werden weiterhin deaktiviert statt gelöscht; Farbvergabe für
  Kalenderblöcke und GPU-Speicher in GB.
- **Anmeldung**: Login per E-Mail-Adresse sowie Selbstregistrierung mit sicherem Passwort
  und doppelter Passwortabfrage. Neue Konten müssen vor der ersten Anmeldung durch einen
  Admin freigegeben werden; der frei wählbare Anzeigename erscheint danach in Kalender,
  Dashboard und Projekten.
- **Design**: PrimeVue-Theme (Aura, Teal-Primärfarbe) mit automatischem Hell-/Dunkelmodus
  und persistierbarem Theme-Umschalter; Farben werden über CSS-Theme-Tokens (`--p-*`) geführt.

## Schnellstart (Docker)

```bash
cp .env.example .env          # SEED_ADMIN_PASSWORD und JWT_SECRET anpassen
docker compose up --build
```

Danach: Frontend auf http://localhost:80, API-Doku auf http://localhost:8000/docs.
Der Seed-Admin wird nur angelegt, wenn noch keine Nutzer existieren.

## Lokale Entwicklung

```bash
# Backend (Python 3.12, uv)
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --port 8000 --reload

# Frontend (Node 20+)
cd frontend
npm install
npm run dev        # http://localhost:5173, Proxyt /api -> :8000
```

### Gates

| Bereich | Befehl |
|---|---|
| Backend-Tests | `uv run pytest` (Backend) |
| Lint/Format | `uv run ruff check . && uv run ruff format --check .` |
| Typecheck | `npm run typecheck` (Frontend) |
| Lint | `npm run lint` |
| Tests | `npm run test` (Vitest: Kalender-Logik + Buchungs-Validierung) |
| Build | `npm run build` |

## Konfiguration (Umgebungsvariablen)

Siehe `.env.example` (Wurzel für Compose) und `backend/.env.example`.

| Variable | Bedeutung |
|---|---|
| `FRONTEND_PORT` | Auf dem Host veröffentlichter Frontend-Port; Default `80` |
| `BACKEND_PORT` | Auf dem Host veröffentlichter direkter Backend-Port; Default `8000` |
| `DATABASE_URL` | SQLAlchemy-URL; Default `sqlite:///./gpu_booking.db` |
| `JWT_SECRET` | Signierschlüssel (Pflicht im Compose-Betrieb; zufällig und ausreichend lang wählen) |
| `JWT_EXPIRE_DAYS` | Token-Gültigkeit (Default 90) |
| `AUTH_COOKIE_SECURE` | Bei HTTPS auf `true`; beschränkt das HttpOnly-Session-Cookie auf TLS |
| `MAX_BOOKING_DAYS` | Maximale Buchungsdauer regulärer Nutzer in ganzen Tagen; Default `7`, Admins unbegrenzt |
| `CORS_ORIGINS` | Erlaubte Frontend-Origins, kommasepariert |
| `VITE_API_BASE_URL` | API-Basis-URL des Frontends; Standard `/api` nutzt den nginx-Proxy. Wird beim Frontend-Image-Build eingebettet. |
| `SEED_ADMIN_DISPLAY_NAME/PASSWORD/EMAIL` | Erster Admin, nur bei leerer Nutzertabelle |

Die beiden `.env.example`-Dateien gehören zu unterschiedlichen Startarten:
`gpu-booking/.env.example` konfiguriert Docker Compose, während
`backend/.env.example` ausschließlich für einen lokal gestarteten Backend-Prozess gedacht ist.

Browser-Sitzungen verwenden ein `HttpOnly`-Cookie mit `SameSite=Strict` sowie einen
CSRF-Header; das JWT wird nicht im Web Storage gespeichert. Frontend und API sollten daher
same-site ausgeliefert werden. Bei einer HTTPS-Bereitstellung muss `AUTH_COOKIE_SECURE=true`
gesetzt sein. Beim Umstieg von einer älteren Version sollte `JWT_SECRET` einmalig rotiert werden,
damit zuvor im Browser gespeicherte Tokens sofort ungültig sind.

## Datenbankmigrationen

Das Backend führt beim Start automatisch `alembic upgrade head` aus. Die Baseline erstellt eine
frische Datenbank vollständig und übernimmt außerdem die bekannten Altschemata mit `username`
beziehungsweise ohne `bookings.server_id`. Ein unbekanntes oder unvollständiges Schema bricht mit
einer eindeutigen Fehlermeldung ab, statt ungeprüft als aktuell markiert zu werden.

Vor dem ersten Start mit bestehenden Produktivdaten sollte wie üblich ein Backup erstellt werden.
Migrationen lassen sich lokal auch explizit prüfen und ausführen:

```bash
cd backend
uv run alembic current
uv run alembic upgrade head
```

## Zeit- und Validierungsregeln

- Zeiten werden als **naive UTC** gespeichert; das Frontend behandelt sie als UTC und
  zeigt sie lokal im deutschen Format `DD.MM.YYYY` und mit 24-Stunden-Uhrzeit an
  (Start/Ende müssen auf vollen Stunden liegen).
- Mindestdauer 1 h, konfigurierbares Maximum über `MAX_BOOKING_DAYS` (Admins ohne Limit);
  Buchungen in der Vergangenheit sind erlaubt.
- Nicht-Mitglieder dürfen für fremde Projekte buchen.

## Projektstruktur

```
backend/   FastAPI + SQLAlchemy, JWT/PBKDF2, atomare Konfliktprüfung, pytest-Suite
frontend/  Vue 3 + TypeScript (strict) + PrimeVue 4, Pinia, Vue Query, vee-validate/Zod, Vitest
compose.yaml  Postgres 18 + Backend + Frontend (nginx)
```
