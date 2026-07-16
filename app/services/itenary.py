"""
app/services/itinerary.py
==========================
Rule-based itinerary generation engine.

Strategy
--------
Given a destination, number of days, and travel style, the builder:
  1. Loads all activities and restaurants for the destination
  2. Groups activities by category (sightseeing, food, adventure, culture, …)
  3. Allocates activities across days based on travel style:
       relaxed  → 2–3 activities/day
       balanced → 3–4 activities/day
       packed   → 5–6 activities/day
  4. Inserts meal recommendations (breakfast / lunch / dinner) each day
  5. Assigns a daily theme based on dominant activity categories
  6. Returns a structured list of ItineraryDay objects
"""

import math
import random
from datetime import datetime, timedelta
from app.models.schemas import ItineraryDay
from app.config import settings


STYLE_ACTIVITIES = {
    "relaxed":  (2, 3),
    "balanced": (3, 4),
    "packed":   (5, 6),
}

DAY_THEMES = {
    "sightseeing": ["Exploring the City", "Iconic Landmarks Day", "City Discovery"],
    "culture":     ["Cultural Immersion", "Arts & History", "Local Heritage"],
    "food":        ["Food & Culinary Tour", "Foodie's Paradise", "Tasting Local Flavours"],
    "adventure":   ["Adventure Day", "Outdoor Thrills", "Action & Exploration"],
    "nature":      ["Nature Escape", "Parks & Scenery", "Into the Wild"],
    "shopping":    ["Shopping & Markets", "Retail Therapy", "Local Boutiques"],
    "relaxation":  ["Rest & Recharge", "Leisurely Stroll", "Slow Travel Day"],
    "nightlife":   ["Nights Out", "Evening Entertainment", "City After Dark"],
}

TRANSPORT_TIPS = [
    "🚇 Use public transport for convenience",
    "🚕 Taxis and rideshares widely available",
    "🚶 Many attractions are walkable",
    "🚴 Bike rentals are popular in this area",
    "🚌 Hop-on hop-off bus covers major sites",
]

TRAVEL_TIPS = [
    "💧 Stay hydrated throughout the day",
    "📸 Best photos in the golden hour",
    "🎫 Book popular attractions in advance",
    "💳 Carry some local currency for small vendors",
    "🗣️ Learn a few local phrases — locals appreciate it!",
    "👟 Wear comfortable shoes for walking",
    "🌤️ Check weather forecast each morning",
]


class ItineraryBuilder:
    """
    Builds a structured day-by-day travel itinerary.

    Usage
    -----
        builder   = ItineraryBuilder()
        itin_data = await builder.build(
            destination=dest,
            activities=activities,
            restaurants=restaurants,
            hotel=hotel,
            request=req,
        )
    """

    def build(
        self,
        destination:  dict,
        activities:   list[dict],
        restaurants:  list[dict],
        hotel:        dict | None,
        start_date:   str,
        num_days:     int,
        num_travelers: int,
        budget_per_day: float,
        travel_style: str = "balanced",
        interests:    list[str] = None,
    ) -> dict:
        """
        Generate a complete itinerary.

        Returns
        -------
        dict with keys: title, destination, hotel, start_date, end_date,
                        num_days, num_travelers, budget_total, days (list)
        """
        interests    = interests or []
        min_acts, max_acts = STYLE_ACTIVITIES.get(travel_style, (3, 4))

        # Filter & prioritise activities by interests
        sorted_acts  = self._prioritise(activities, interests)
        restaurants_by_meal = self._group_restaurants(restaurants)

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = start_dt + timedelta(days=num_days - 1)

        days = []
        act_pool = list(sorted_acts)   # mutable pool

        for day_num in range(1, num_days + 1):
            day_dt    = start_dt + timedelta(days=day_num - 1)
            day_date  = day_dt.strftime("%Y-%m-%d")
            day_label = day_dt.strftime("%A, %d %B %Y")

            # Pick activities for the day
            acts_today = self._pick_activities(act_pool, min_acts, max_acts)
            # Remove used activities to avoid repetition
            for a in acts_today:
                if a in act_pool:
                    act_pool.remove(a)
            if not act_pool:   # replenish if exhausted
                act_pool = list(sorted_acts)

            # Split into time slots
            morning, afternoon, evening = self._schedule_activities(
                acts_today, day_num, num_days, travel_style)

            # Meals
            meals = self._assign_meals(
                restaurants_by_meal, day_num, hotel)

            # Day theme
            theme = self._day_theme(day_num, acts_today, num_days)

            # Notes
            tip = random.choice(TRAVEL_TIPS)
            transport = random.choice(TRANSPORT_TIPS)

            days.append({
                "day_number": day_num,
                "date":       day_date,
                "date_label": day_label,
                "theme":      theme,
                "morning":    morning,
                "afternoon":  afternoon,
                "evening":    evening,
                "meals":      meals,
                "notes":      f"{tip}  ·  {transport}",
            })

        budget_total = budget_per_day * num_days * num_travelers
        hotel_name   = hotel["name"] if hotel else "TBD"

        title = (
            f"{num_days}-Day {destination['name']} "
            f"{'Adventure' if travel_style=='packed' else 'Getaway'}"
        )

        return {
            "title":         title,
            "destination":   destination["name"],
            "country":       destination.get("country",""),
            "hotel":         hotel_name,
            "start_date":    start_date,
            "end_date":      end_dt.strftime("%Y-%m-%d"),
            "num_days":      num_days,
            "num_travelers": num_travelers,
            "budget_per_day": budget_per_day,
            "budget_total":  round(budget_total, 2),
            "travel_style":  travel_style,
            "days":          days,
        }

    # ── Activity helpers ──────────────────────────────────────────────────────

    def _prioritise(self, activities: list[dict], interests: list[str]) -> list[dict]:
        if not interests:
            return sorted(activities, key=lambda x: x.get("rating",0), reverse=True)
        def score(a):
            base   = a.get("rating", 0)
            boost  = 5 if a.get("category","") in interests else 0
            return base + boost
        return sorted(activities, key=score, reverse=True)

    def _pick_activities(self, pool: list[dict], min_n: int, max_n: int) -> list[dict]:
        n = random.randint(min_n, min(max_n, len(pool)))
        return pool[:n]

    def _schedule_activities(
        self,
        acts: list[dict],
        day_num: int,
        total_days: int,
        style: str,
    ) -> tuple[list, list, list]:
        morning   = []
        afternoon = []
        evening   = []

        for i, act in enumerate(acts):
            slot = i % 3
            event = {
                "time":     ["9:00 AM","10:30 AM","11:00 AM"][i % 3] if slot == 0
                            else ["2:00 PM","3:00 PM","4:00 PM"][i % 3] if slot == 1
                            else ["7:00 PM","8:00 PM"][i % 2],
                "name":     act["name"],
                "emoji":    act.get("image_emoji","🎯"),
                "duration": f"{act.get('duration_hours',2):.0f}h",
                "cost":     f"${act.get('cost_usd',0):.0f}" if act.get("cost_usd") else "Free",
                "category": act.get("category",""),
                "tip":      act.get("description","")[:100],
            }
            if slot == 0:    morning.append(event)
            elif slot == 1:  afternoon.append(event)
            else:            evening.append(event)

        # First/last day specials
        if day_num == 1:
            morning.insert(0, {
                "time": "8:00 AM", "name": "Hotel Check-In & Orientation",
                "emoji": "🏨", "duration": "1h", "cost": "—",
                "category": "logistics", "tip": "Drop bags and get oriented.",
            })
        if day_num == total_days:
            evening.append({
                "time": "10:00 AM", "name": "Hotel Check-Out & Departure",
                "emoji": "🧳", "duration": "1h", "cost": "—",
                "category": "logistics", "tip": "Confirm departure transport.",
            })

        return morning, afternoon, evening

    # ── Meal helpers ──────────────────────────────────────────────────────────

    def _group_restaurants(self, restaurants: list[dict]) -> dict:
        by_meal = {"breakfast": [], "lunch": [], "dinner": []}
        for r in restaurants:
            mt = r.get("meal_type","lunch,dinner")
            for meal in ["breakfast","lunch","dinner"]:
                if meal in mt:
                    by_meal[meal].append(r)
        return by_meal

    def _assign_meals(self, by_meal: dict, day_num: int, hotel: dict) -> dict:
        def pick(meal_list: list) -> dict | None:
            if not meal_list:
                return None
            idx = (day_num - 1) % len(meal_list)
            r   = meal_list[idx]
            return {
                "name":    r["name"],
                "cuisine": r.get("cuisine","Local"),
                "price":   r.get("price_range","$$"),
                "emoji":   r.get("image_emoji","🍽️"),
                "rating":  r.get("rating",4.0),
            }

        meals: dict = {}

        # Breakfast at hotel if available
        if hotel and hotel.get("breakfast"):
            meals["breakfast"] = {
                "name":    f"Breakfast at {hotel['name']}",
                "cuisine": "Buffet",
                "price":   "Included",
                "emoji":   "🍳",
                "rating":  hotel.get("avg_rating",4.0),
            }
        else:
            meals["breakfast"] = pick(by_meal["breakfast"]) or {
                "name": "Local café", "cuisine": "Café", "price": "$", "emoji": "☕", "rating": 4.0}

        meals["lunch"]  = pick(by_meal["lunch"]) or {
            "name": "Local restaurant", "cuisine": "Local", "price": "$$", "emoji": "🍜", "rating": 4.0}
        meals["dinner"] = pick(by_meal["dinner"]) or {
            "name": "Evening dining", "cuisine": "Local", "price": "$$$", "emoji": "🍷", "rating": 4.3}

        return meals

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _day_theme(self, day_num: int, acts: list[dict], total_days: int) -> str:
        if not acts:
            return f"Day {day_num} — Free Exploration"

        cats = [a.get("category","sightseeing") for a in acts]
        dominant = max(set(cats), key=cats.count)
        options  = DAY_THEMES.get(dominant, [f"Day {day_num} Exploration"])
        idx      = (day_num - 1) % len(options)
        return options[idx]