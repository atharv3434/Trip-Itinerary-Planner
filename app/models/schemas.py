"""
app/models/schemas.py — Pydantic request/response schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class HotelSearchParams(BaseModel):
    destination:  str   = Field(..., min_length=2)
    check_in:     str   = ""
    check_out:    str   = ""
    guests:       int   = Field(default=2, ge=1, le=20)
    min_stars:    int   = Field(default=1, ge=1, le=5)
    max_stars:    int   = Field(default=5, ge=1, le=5)
    min_price:    float = Field(default=0, ge=0)
    max_price:    float = Field(default=9999, ge=0)
    hotel_type:   Optional[str] = None
    sort_by:      str   = "rating"
    wifi:         bool  = False
    pool:         bool  = False
    gym:          bool  = False
    spa:          bool  = False
    breakfast:    bool  = False
    parking:      bool  = False
    pet_friendly: bool  = False


class ItineraryRequest(BaseModel):
    destination_id: int
    hotel_id:       Optional[int] = None
    start_date:     str
    end_date:       str
    num_travelers:  int   = Field(default=2, ge=1)
    budget_per_day: float = Field(default=200, ge=0)
    travel_style:   str   = "balanced"   # relaxed | balanced | packed
    interests:      list[str] = []
    notes:          str   = ""

    @field_validator("travel_style")
    @classmethod
    def valid_style(cls, v):
        if v not in ("relaxed","balanced","packed"):
            raise ValueError("travel_style must be relaxed, balanced, or packed")
        return v


class HotelResult(BaseModel):
    id:              int
    name:            str
    star_rating:     int
    price_per_night: float
    avg_rating:      float
    review_count:    int
    hotel_type:      str
    image_emoji:     str
    amenities:       list[str]
    recommendation_score: float = 0.0
    destination_name: str = ""


class ItineraryDay(BaseModel):
    day_number:  int
    date:        str
    theme:       str
    morning:     list[dict]
    afternoon:   list[dict]
    evening:     list[dict]
    meals:       dict


class ItineraryResult(BaseModel):
    title:        str
    destination:  str
    hotel:        Optional[str]
    start_date:   str
    end_date:     str
    num_days:     int
    num_travelers: int
    budget_total: float
    days:         list[ItineraryDay]