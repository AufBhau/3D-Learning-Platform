# 3D Learning Platform

A Django web app for teaching with interactive 3D models. Students explore `.glb` / `.gltf` lessons in the browser, click hotspots on important parts, and track progress. Educators create courses, upload models, and place annotations in a visual editor.

**Live idea:** open a course → load a lesson → orbit the model → follow numbered hotspots along a learning path.

## Features

- **3D lesson viewer** — Three.js viewer with orbit, zoom, wireframe, auto-rotate, and hotspot labels
- **Hotspots / annotations** — Clickable markers on the model with titles and explanations
- **Visual learning path** — Ordered lesson flow so students know what to explore next
- **Student & educator roles** — Public signup is student-only; educators are granted via Django admin
- **Course management** — Educators create courses, lessons, upload models, and place hotspots
- **Progress tracking** — Mark lessons complete and see per-course completion
- **REST API** — Course/lesson/progress endpoints plus educator CRUD via Django REST Framework
- **Demo seed** — One command creates a sample course, box model, and hotspots

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Django 4.2, Django REST Framework |
| Frontend | Django templates, vanilla JS, Three.js |
| Database | SQLite (default) |
| Media | Pillow (thumbnails), `.glb` / `.gltf` models |

## Quick start

### Requirements

- Python 3.10+ recommended
- pip / venv

### Setup

```bash
# Clone
git clone https://github.com/AufBhau/3D-Learning-Platform.git
cd 3D-Learning-Platform

# Virtualenv
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Environment
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux

# Database
python manage.py migrate

# Optional demo course + 3D box
python manage.py seed_demo

# Run
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

### Environment variables

Copy `.env.example` to `.env` (loaded automatically). Defaults are fail-closed: `DEBUG` is off unless set, and `DJANGO_SECRET_KEY` is required when `DEBUG` is false.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Secret key (required when `DJANGO_DEBUG` is not `True`) |
| `DJANGO_DEBUG` | `True` / `False` (default `False`) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF (e.g. `https://your-domain.com`) |

See `learning_platform/settings.py`.

**Production static/media:** WhiteNoise serves collected static files when `DEBUG=False`. Uploaded media stays on local disk (`MEDIA_ROOT`) and is served when `DJANGO_SERVE_MEDIA=True` (default) — suitable for PythonAnywhere. After deploy: `pip install -r requirements.txt`, `migrate`, `collectstatic`, then reload the web app.

### Create an educator

1. Sign up at `/accounts/signup/` (always creates a **student**)
2. In Django admin (`/admin/`), set the user’s profile role to **Educator**
3. Or create a superuser: `python manage.py createsuperuser`

Educators use `/educator/` for the dashboard, course/lesson forms, and hotspot placement.

### Tests

```bash
python manage.py test
```

## Project structure

```
3d-learning-platform/
├── accounts/           # Auth, profiles, student/educator roles
├── courses/            # Courses, lessons, annotations, progress, APIs
│   ├── management/commands/seed_demo.py
│   └── templates/courses/
├── learning_platform/  # Django project settings & URLs
├── media/              # Uploaded models & thumbnails (demo assets included)
├── static/             # CSS + Three.js lesson viewer / hotspot placer
├── templates/          # Shared base template
├── manage.py
├── requirements.txt
└── .env.example
```

## Main routes

| Path | Description |
| --- | --- |
| `/` | Home / featured courses |
| `/courses/` | Course list |
| `/courses/<id>/` | Course detail & lesson path |
| `/viewer/<lesson_id>/` | Interactive 3D lesson viewer |
| `/accounts/` | Login, signup, profile |
| `/educator/` | Educator dashboard & editors |
| `/api/` | REST API |
| `/admin/` | Django admin |

### API (selection)

- `GET /api/courses/` — list courses  
- `GET /api/courses/<id>/` — course detail  
- `GET /api/lessons/<id>/` — lesson + annotations  
- `POST /api/lessons/<id>/complete/` — mark complete (auth)  
- `GET /api/me/progress/` — current user’s progress  
- `/api/educator/courses|lessons|annotations/` — educator ViewSets  

Browse the API at `/api/` when the server is running (session auth supported).

## Using the 3D viewer

1. Browse a course and open a lesson with a `.glb` / `.gltf` model.
2. Drag to orbit, scroll to zoom.
3. Click numbered hotspots (or the sidebar list) to read callouts.
4. Mark the lesson complete when finished; progress shows on your profile and course pages.

Educators can place hotspots visually from the educator tools without editing raw coordinates by hand.

## Demo data

```bash
python manage.py seed_demo
```

Creates **Demo: Explore a Box** with a generated box `.glb` and three face hotspots. Open the printed `/viewer/<id>/` URL after seeding.

## Development notes

- Static assets live in `static/`; media uploads go to `media/`.
- Demo models and course thumbnails under `media/3d_models/` and `media/course_thumbnails/` are kept in the repo for a working local/demo site.
- With `DEBUG=False`, configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`, then run `python manage.py collectstatic`.
- Login attempts are rate-limited; API requests use DRF anon/user throttles.

## License

No license file is included yet. Add one if you want others to reuse this project under clear terms.
