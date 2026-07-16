# 🌍 Trip Planner — Hotel Recommendations & Itinerary Builder

A full-stack travel planning web app built with FastAPI + Jinja2.
Search hotels, get smart recommendations, and generate beautiful day-by-day itineraries.

---

## ✨ Features

- 🏨 **Hotel Recommendations** — filter by destination, budget, star rating, amenities
- 📅 **Itinerary Builder** — AI-style day-by-day trip planner
- 🗺️ **Destination Guides** — top activities, restaurants, transport tips
- 💾 **Save Trips** — store and revisit planned itineraries
- 📄 **Export Itinerary** — download as formatted text
- 🔍 **Smart Search** — multi-filter hotel search with scoring engine

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python seed_data.py      # populate database with sample hotels & destinations
python main.py
# Open http://localhost:8000
```

---

## 📁 Project Structure

```
trip-planner/
├── main.py                          # FastAPI entry point
├── seed_data.py                     # Database seeding script
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                # All web + API routes
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py              # SQLite async database
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py               # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── recommender.py           # Hotel recommendation engine
│   │   └── itinerary.py             # Itinerary generation engine
│   └── utils/
│       ├── __init__.py
│       └── helpers.py               # Date, formatting utilities
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html               # Home / search page
│   │   ├── hotels.html              # Hotel results
│   │   ├── hotel_detail.html        # Single hotel page
│   │   ├── itinerary.html           # Itinerary viewer
│   │   └── my_trips.html            # Saved trips
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/
│   └── destinations.json            # Destination data
├── tests/
│   └── test_services.py
└── outputs/
    └── itineraries/                 # Exported itinerary files
```

---

## 🌐 Routes

| Route | Description |
|-------|-------------|
| `GET /` | Home — destination search |
| `GET /hotels` | Hotel search results |
| `GET /hotels/{id}` | Hotel detail page |
| `POST /itinerary/generate` | Generate a trip itinerary |
| `GET /itinerary/{id}` | View saved itinerary |
| `GET /my-trips` | All saved trips |
| `GET /api/hotels/search` | JSON hotel search API |
| `GET /api/destinations` | JSON destination list |
| `POST /api/itinerary/export` | Download itinerary as text |