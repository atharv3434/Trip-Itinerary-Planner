"""
app/db/database.py
==================
Async SQLite database layer using aiosqlite.

Tables
------
  destinations  — city/country info, timezone, currency
  hotels        — full hotel profiles with amenities
  activities    — things to do in each destination
  restaurants   — dining options per destination
  itineraries   — saved trip plans
  itinerary_days— day-by-day breakdown of an itinerary
"""

import os
import time
import json
import aiosqlite

DB_PATH = "./outputs/tripplanner.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS destinations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    country      TEXT NOT NULL,
    description  TEXT DEFAULT '',
    timezone     TEXT DEFAULT 'UTC',
    currency     TEXT DEFAULT 'USD',
    language     TEXT DEFAULT 'English',
    best_season  TEXT DEFAULT '',
    avg_temp_c   REAL DEFAULT 20.0,
    image_emoji  TEXT DEFAULT '🌍',
    tags         TEXT DEFAULT '',    -- JSON array
    created_at   REAL NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS hotels (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id  INTEGER NOT NULL,
    name            TEXT NOT NULL,
    star_rating     INTEGER NOT NULL DEFAULT 3,
    price_per_night REAL NOT NULL,
    currency        TEXT DEFAULT 'USD',
    address         TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    amenities       TEXT DEFAULT '',  -- JSON array
    image_emoji     TEXT DEFAULT '🏨',
    review_count    INTEGER DEFAULT 0,
    avg_rating      REAL DEFAULT 4.0,
    hotel_type      TEXT DEFAULT 'hotel',
    cancellation    TEXT DEFAULT 'Free cancellation',
    breakfast       INTEGER DEFAULT 0,
    pool            INTEGER DEFAULT 0,
    gym             INTEGER DEFAULT 0,
    spa             INTEGER DEFAULT 0,
    wifi            INTEGER DEFAULT 1,
    parking         INTEGER DEFAULT 0,
    pet_friendly    INTEGER DEFAULT 0,
    created_at      REAL NOT NULL DEFAULT (unixepoch()),
    FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id INTEGER NOT NULL,
    name           TEXT NOT NULL,
    category       TEXT DEFAULT 'sightseeing',
    description    TEXT DEFAULT '',
    duration_hours REAL DEFAULT 2.0,
    cost_usd       REAL DEFAULT 0.0,
    best_time      TEXT DEFAULT 'Morning',
    image_emoji    TEXT DEFAULT '🎯',
    rating         REAL DEFAULT 4.0,
    tags           TEXT DEFAULT '',
    FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurants (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id INTEGER NOT NULL,
    name           TEXT NOT NULL,
    cuisine        TEXT DEFAULT 'Local',
    meal_type      TEXT DEFAULT 'lunch,dinner',
    price_range    TEXT DEFAULT '$$',
    description    TEXT DEFAULT '',
    image_emoji    TEXT DEFAULT '🍽️',
    rating         REAL DEFAULT 4.0,
    FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS itineraries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    destination_id INTEGER NOT NULL,
    hotel_id       INTEGER,
    start_date     TEXT NOT NULL,
    end_date       TEXT NOT NULL,
    num_days       INTEGER NOT NULL,
    num_travelers  INTEGER DEFAULT 1,
    budget_total   REAL DEFAULT 0,
    budget_per_day REAL DEFAULT 0,
    travel_style   TEXT DEFAULT 'balanced',
    notes          TEXT DEFAULT '',
    created_at     REAL NOT NULL DEFAULT (unixepoch()),
    FOREIGN KEY (destination_id) REFERENCES destinations(id),
    FOREIGN KEY (hotel_id)       REFERENCES hotels(id)
);

CREATE TABLE IF NOT EXISTS itinerary_days (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id   INTEGER NOT NULL,
    day_number     INTEGER NOT NULL,
    date           TEXT NOT NULL,
    theme          TEXT DEFAULT '',
    morning        TEXT DEFAULT '',   -- JSON list of events
    afternoon      TEXT DEFAULT '',
    evening        TEXT DEFAULT '',
    meals          TEXT DEFAULT '',   -- JSON {breakfast, lunch, dinner}
    notes          TEXT DEFAULT '',
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hotels_dest   ON hotels(destination_id);
CREATE INDEX IF NOT EXISTS idx_hotels_price  ON hotels(price_per_night);
CREATE INDEX IF NOT EXISTS idx_hotels_stars  ON hotels(star_rating);
CREATE INDEX IF NOT EXISTS idx_activities_dest ON activities(destination_id);
CREATE INDEX IF NOT EXISTS idx_itin_dest     ON itineraries(destination_id);
"""


async def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("outputs/itineraries", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


# ── Destinations ──────────────────────────────────────────────────────────────

async def get_all_destinations():
    async with await get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM destinations ORDER BY name")
        return [dict(r) for r in rows]


async def get_destination(dest_id: int):
    async with await get_db() as db:
        row = await db.execute_fetchone(
            "SELECT * FROM destinations WHERE id=?", (dest_id,))
        return dict(row) if row else None


async def get_destination_by_name(name: str):
    async with await get_db() as db:
        row = await db.execute_fetchone(
            "SELECT * FROM destinations WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",))
        return dict(row) if row else None


async def search_destinations(query: str):
    async with await get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM destinations WHERE LOWER(name) LIKE LOWER(?) OR LOWER(country) LIKE LOWER(?)",
            (f"%{query}%", f"%{query}%"))
        return [dict(r) for r in rows]


# ── Hotels ────────────────────────────────────────────────────────────────────

async def get_hotels(
    destination_id: int = None,
    min_stars: int = 1,
    max_stars: int = 5,
    min_price: float = 0,
    max_price: float = 9999,
    hotel_type: str = None,
    amenities: list = None,
    sort_by: str = "rating",
    limit: int = 20,
    offset: int = 0,
):
    async with await get_db() as db:
        query = """
            SELECT h.*, d.name as destination_name, d.country
            FROM hotels h JOIN destinations d ON d.id=h.destination_id
            WHERE h.star_rating BETWEEN ? AND ?
              AND h.price_per_night BETWEEN ? AND ?
        """
        params = [min_stars, max_stars, min_price, max_price]

        if destination_id:
            query += " AND h.destination_id=?"
            params.append(destination_id)

        if hotel_type:
            query += " AND h.hotel_type=?"
            params.append(hotel_type)

        if amenities:
            for am in amenities:
                query += f" AND h.{am}=1"

        order_map = {
            "rating":   "h.avg_rating DESC, h.review_count DESC",
            "price_asc":  "h.price_per_night ASC",
            "price_desc": "h.price_per_night DESC",
            "stars":    "h.star_rating DESC",
        }
        query += f" ORDER BY {order_map.get(sort_by, 'h.avg_rating DESC')}"
        query += " LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = await db.execute_fetchall(query, params)
        return [dict(r) for r in rows]


async def get_hotel(hotel_id: int):
    async with await get_db() as db:
        row = await db.execute_fetchone(
            """SELECT h.*, d.name as destination_name, d.country, d.currency
               FROM hotels h JOIN destinations d ON d.id=h.destination_id
               WHERE h.id=?""", (hotel_id,))
        return dict(row) if row else None


async def insert_hotel(data: dict) -> int:
    async with await get_db() as db:
        cur = await db.execute("""
            INSERT INTO hotels (destination_id,name,star_rating,price_per_night,
                currency,address,description,amenities,image_emoji,review_count,
                avg_rating,hotel_type,cancellation,breakfast,pool,gym,spa,wifi,
                parking,pet_friendly)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["destination_id"], data["name"], data["star_rating"],
            data["price_per_night"], data.get("currency","USD"),
            data.get("address",""), data.get("description",""),
            json.dumps(data.get("amenities",[])), data.get("image_emoji","🏨"),
            data.get("review_count",0), data.get("avg_rating",4.0),
            data.get("hotel_type","hotel"), data.get("cancellation","Free cancellation"),
            int(data.get("breakfast",0)), int(data.get("pool",0)),
            int(data.get("gym",0)), int(data.get("spa",0)),
            int(data.get("wifi",1)), int(data.get("parking",0)),
            int(data.get("pet_friendly",0)),
        ))
        await db.commit()
        return cur.lastrowid


# ── Activities ────────────────────────────────────────────────────────────────

async def get_activities(destination_id: int, category: str = None, limit: int = 30):
    async with await get_db() as db:
        if category:
            rows = await db.execute_fetchall(
                "SELECT * FROM activities WHERE destination_id=? AND category=? ORDER BY rating DESC LIMIT ?",
                (destination_id, category, limit))
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM activities WHERE destination_id=? ORDER BY rating DESC LIMIT ?",
                (destination_id, limit))
        return [dict(r) for r in rows]


async def insert_activity(data: dict) -> int:
    async with await get_db() as db:
        cur = await db.execute("""
            INSERT INTO activities (destination_id,name,category,description,
                duration_hours,cost_usd,best_time,image_emoji,rating,tags)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data["destination_id"], data["name"], data.get("category","sightseeing"),
            data.get("description",""), data.get("duration_hours",2.0),
            data.get("cost_usd",0.0), data.get("best_time","Morning"),
            data.get("image_emoji","🎯"), data.get("rating",4.0),
            data.get("tags",""),
        ))
        await db.commit()
        return cur.lastrowid


# ── Restaurants ───────────────────────────────────────────────────────────────

async def get_restaurants(destination_id: int, meal_type: str = None, limit: int = 20):
    async with await get_db() as db:
        if meal_type:
            rows = await db.execute_fetchall(
                "SELECT * FROM restaurants WHERE destination_id=? AND meal_type LIKE ? ORDER BY rating DESC LIMIT ?",
                (destination_id, f"%{meal_type}%", limit))
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM restaurants WHERE destination_id=? ORDER BY rating DESC LIMIT ?",
                (destination_id, limit))
        return [dict(r) for r in rows]


async def insert_restaurant(data: dict) -> int:
    async with await get_db() as db:
        cur = await db.execute("""
            INSERT INTO restaurants (destination_id,name,cuisine,meal_type,
                price_range,description,image_emoji,rating)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            data["destination_id"], data["name"], data.get("cuisine","Local"),
            data.get("meal_type","lunch,dinner"), data.get("price_range","$$"),
            data.get("description",""), data.get("image_emoji","🍽️"),
            data.get("rating",4.0),
        ))
        await db.commit()
        return cur.lastrowid


async def insert_destination(data: dict) -> int:
    async with await get_db() as db:
        cur = await db.execute("""
            INSERT INTO destinations (name,country,description,timezone,currency,
                language,best_season,avg_temp_c,image_emoji,tags)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data["name"], data["country"], data.get("description",""),
            data.get("timezone","UTC"), data.get("currency","USD"),
            data.get("language","English"), data.get("best_season",""),
            data.get("avg_temp_c",20.0), data.get("image_emoji","🌍"),
            json.dumps(data.get("tags",[])),
        ))
        await db.commit()
        return cur.lastrowid


# ── Itineraries ───────────────────────────────────────────────────────────────

async def save_itinerary(itin: dict, days: list) -> int:
    async with await get_db() as db:
        cur = await db.execute("""
            INSERT INTO itineraries (title,destination_id,hotel_id,start_date,end_date,
                num_days,num_travelers,budget_total,budget_per_day,travel_style,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            itin["title"], itin["destination_id"], itin.get("hotel_id"),
            itin["start_date"], itin["end_date"], itin["num_days"],
            itin.get("num_travelers",1), itin.get("budget_total",0),
            itin.get("budget_per_day",0), itin.get("travel_style","balanced"),
            itin.get("notes",""), time.time(),
        ))
        itin_id = cur.lastrowid

        for day in days:
            await db.execute("""
                INSERT INTO itinerary_days (itinerary_id,day_number,date,theme,
                    morning,afternoon,evening,meals,notes)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                itin_id, day["day_number"], day["date"], day.get("theme",""),
                json.dumps(day.get("morning",[])),
                json.dumps(day.get("afternoon",[])),
                json.dumps(day.get("evening",[])),
                json.dumps(day.get("meals",{})),
                day.get("notes",""),
            ))
        await db.commit()
        return itin_id


async def get_itinerary(itin_id: int):
    async with await get_db() as db:
        row = await db.execute_fetchone("""
            SELECT i.*, d.name as dest_name, d.country, d.image_emoji as dest_emoji,
                   h.name as hotel_name, h.star_rating, h.price_per_night
            FROM itineraries i
            JOIN destinations d ON d.id=i.destination_id
            LEFT JOIN hotels h ON h.id=i.hotel_id
            WHERE i.id=?
        """, (itin_id,))
        if not row:
            return None
        itin = dict(row)
        days = await db.execute_fetchall(
            "SELECT * FROM itinerary_days WHERE itinerary_id=? ORDER BY day_number",
            (itin_id,))
        itin["days"] = []
        for d in days:
            day = dict(d)
            day["morning"]   = json.loads(day["morning"]   or "[]")
            day["afternoon"] = json.loads(day["afternoon"] or "[]")
            day["evening"]   = json.loads(day["evening"]   or "[]")
            day["meals"]     = json.loads(day["meals"]     or "{}")
            itin["days"].append(day)
        return itin


async def get_all_itineraries():
    async with await get_db() as db:
        rows = await db.execute_fetchall("""
            SELECT i.*, d.name as dest_name, d.country, d.image_emoji as dest_emoji
            FROM itineraries i
            JOIN destinations d ON d.id=i.destination_id
            ORDER BY i.created_at DESC
        """)
        return [dict(r) for r in rows]


async def delete_itinerary(itin_id: int):
    async with await get_db() as db:
        await db.execute("DELETE FROM itineraries WHERE id=?", (itin_id,))
        await db.commit()