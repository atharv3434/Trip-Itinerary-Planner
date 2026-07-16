"""
app/api/routes.py — All web page and API routes
"""

import json
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.db.database import (
    get_all_destinations, get_destination, get_destination_by_name,
    search_destinations, get_hotels, get_hotel, get_activities,
    get_restaurants, save_itinerary, get_itinerary, get_all_itineraries,
    delete_itinerary,
)
from app.services.recommender import HotelRecommender
from app.services.itinerary   import ItineraryBuilder
from app.utils.helpers        import nights_between, format_currency, export_itinerary_text

router     = APIRouter()
templates  = Jinja2Templates(directory="frontend/templates")
recommender = HotelRecommender()
builder     = ItineraryBuilder()


# ── Home ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    destinations = await get_all_destinations()
    return templates.TemplateResponse("index.html", {
        "request":      request,
        "destinations": destinations,
        "today":        datetime.today().strftime("%Y-%m-%d"),
        "tomorrow":     (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
    })


# ── Hotel search ──────────────────────────────────────────────────────────────

@router.get("/hotels", response_class=HTMLResponse)
async def hotel_search_page(
    request:    Request,
    destination: str  = "",
    check_in:   str  = "",
    check_out:  str  = "",
    guests:     int  = 2,
    min_stars:  int  = 1,
    max_stars:  int  = 5,
    min_price:  float = 0,
    max_price:  float = 9999,
    hotel_type: str  = "",
    sort_by:    str  = "rating",
    wifi:       str  = "",
    pool:       str  = "",
    gym:        str  = "",
    spa:        str  = "",
    breakfast:  str  = "",
    parking:    str  = "",
    pet_friendly: str= "",
):
    dest_obj  = None
    hotels    = []
    dest_id   = None

    if destination:
        dest_obj = await get_destination_by_name(destination)
        if dest_obj:
            dest_id = dest_obj["id"]

    amenity_filters = []
    amenity_bools   = {}
    for am in ["wifi","pool","gym","spa","breakfast","parking","pet_friendly"]:
        val = locals().get(am, "")
        if val in ("on","1","true","yes"):
            amenity_filters.append(am)
            amenity_bools[am] = True
        else:
            amenity_bools[am] = False

    raw_hotels = await get_hotels(
        destination_id = dest_id,
        min_stars = min_stars,
        max_stars = max_stars,
        min_price = min_price,
        max_price = max_price if max_price < 9999 else 9999,
        hotel_type = hotel_type or None,
        sort_by   = sort_by,
        limit     = 50,
    )

    budget = (min_price + max_price) / 2 if max_price < 9999 else None
    hotels = recommender.rank(raw_hotels, amenity_filters, budget)

    nights = nights_between(check_in, check_out) if check_in and check_out else 1

    destinations = await get_all_destinations()

    return templates.TemplateResponse("hotels.html", {
        "request":      request,
        "hotels":       hotels,
        "destination":  destination,
        "dest_obj":     dest_obj,
        "destinations": destinations,
        "check_in":     check_in,
        "check_out":    check_out,
        "guests":       guests,
        "nights":       nights,
        "min_stars":    min_stars,
        "max_stars":    max_stars,
        "min_price":    min_price,
        "max_price":    max_price if max_price < 9999 else "",
        "hotel_type":   hotel_type,
        "sort_by":      sort_by,
        "amenity_bools": amenity_bools,
        "total_found":  len(hotels),
    })


@router.get("/hotels/{hotel_id}", response_class=HTMLResponse)
async def hotel_detail(request: Request, hotel_id: int):
    hotel = await get_hotel(hotel_id)
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    amenities = json.loads(hotel.get("amenities","[]") or "[]")
    hotel["amenities_list"] = amenities
    dest = await get_destination(hotel["destination_id"])
    activities = await get_activities(hotel["destination_id"], limit=6)
    return templates.TemplateResponse("hotel_detail.html", {
        "request":    request,
        "hotel":      hotel,
        "dest":       dest,
        "activities": activities,
        "today":      datetime.today().strftime("%Y-%m-%d"),
        "checkout":   (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
    })


# ── Itinerary ─────────────────────────────────────────────────────────────────

@router.get("/plan", response_class=HTMLResponse)
async def plan_page(request: Request, destination_id: int = 0, hotel_id: int = 0):
    destinations = await get_all_destinations()
    dest = await get_destination(destination_id) if destination_id else None
    hotel = await get_hotel(hotel_id) if hotel_id else None
    today = datetime.today().strftime("%Y-%m-%d")
    checkout = (datetime.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    return templates.TemplateResponse("plan.html", {
        "request":      request,
        "destinations": destinations,
        "dest":         dest,
        "hotel":        hotel,
        "today":        today,
        "checkout":     checkout,
    })


@router.post("/itinerary/generate", response_class=HTMLResponse)
async def generate_itinerary(
    request:        Request,
    destination_id: int   = Form(...),
    hotel_id:       int   = Form(0),
    start_date:     str   = Form(...),
    end_date:       str   = Form(...),
    num_travelers:  int   = Form(2),
    budget_per_day: float = Form(200),
    travel_style:   str   = Form("balanced"),
    interests:      str   = Form(""),
    notes:          str   = Form(""),
):
    dest  = await get_destination(destination_id)
    if not dest:
        raise HTTPException(404, "Destination not found")

    hotel = await get_hotel(hotel_id) if hotel_id else None
    activities  = await get_activities(destination_id, limit=40)
    restaurants = await get_restaurants(destination_id, limit=30)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")
    num_days = max(1, (end_dt - start_dt).days + 1)

    interest_list = [i.strip() for i in interests.split(",") if i.strip()]

    itin_data = builder.build(
        destination   = dest,
        activities    = activities,
        restaurants   = restaurants,
        hotel         = hotel,
        start_date    = start_date,
        num_days      = num_days,
        num_travelers = num_travelers,
        budget_per_day = budget_per_day,
        travel_style  = travel_style,
        interests     = interest_list,
    )

    # Persist to DB
    itin_db = {
        "title":          itin_data["title"],
        "destination_id": destination_id,
        "hotel_id":       hotel_id or None,
        "start_date":     start_date,
        "end_date":       end_date,
        "num_days":       num_days,
        "num_travelers":  num_travelers,
        "budget_total":   itin_data["budget_total"],
        "budget_per_day": budget_per_day,
        "travel_style":   travel_style,
        "notes":          notes,
    }
    itin_id = await save_itinerary(itin_db, itin_data["days"])

    return templates.TemplateResponse("itinerary.html", {
        "request":   request,
        "itin":      itin_data,
        "itin_id":   itin_id,
        "dest":      dest,
        "hotel":     hotel,
        "format_currency": format_currency,
    })


@router.get("/itinerary/{itin_id}", response_class=HTMLResponse)
async def view_itinerary(request: Request, itin_id: int):
    itin = await get_itinerary(itin_id)
    if not itin:
        raise HTTPException(404, "Itinerary not found")
    dest  = await get_destination(itin["destination_id"])
    hotel = await get_hotel(itin["hotel_id"]) if itin.get("hotel_id") else None
    return templates.TemplateResponse("itinerary.html", {
        "request":   request,
        "itin":      itin,
        "itin_id":   itin_id,
        "dest":      dest,
        "hotel":     hotel,
        "format_currency": format_currency,
    })


@router.get("/my-trips", response_class=HTMLResponse)
async def my_trips(request: Request):
    itins = await get_all_itineraries()
    return templates.TemplateResponse("my_trips.html", {
        "request": request,
        "itins":   itins,
    })


@router.post("/my-trips/{itin_id}/delete")
async def del_trip(itin_id: int):
    await delete_itinerary(itin_id)
    return JSONResponse({"ok": True})


# ── JSON API ──────────────────────────────────────────────────────────────────

@router.get("/api/destinations")
async def api_destinations(q: str = ""):
    if q:
        return await search_destinations(q)
    return await get_all_destinations()


@router.get("/api/hotels/search")
async def api_hotel_search(
    destination_id: int   = 0,
    min_stars:      int   = 1,
    max_stars:      int   = 5,
    min_price:      float = 0,
    max_price:      float = 9999,
    sort_by:        str   = "rating",
    limit:          int   = 20,
):
    hotels = await get_hotels(
        destination_id = destination_id or None,
        min_stars = min_stars, max_stars = max_stars,
        min_price = min_price, max_price = max_price,
        sort_by = sort_by, limit = limit,
    )
    return recommender.rank(hotels)


@router.get("/api/itinerary/{itin_id}/export")
async def export_itinerary(itin_id: int):
    itin = await get_itinerary(itin_id)
    if not itin:
        raise HTTPException(404, "Itinerary not found")
    text     = export_itinerary_text(itin)
    filename = f"itinerary_{itin_id}.txt"
    filepath = os.path.join("outputs/itineraries", filename)
    os.makedirs("outputs/itineraries", exist_ok=True)
    with open(filepath, "w") as f:
        f.write(text)
    return FileResponse(filepath, filename=filename, media_type="text/plain")