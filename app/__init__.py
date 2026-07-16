"""
Trip Planner — Hotel Recommendations & Itinerary Builder
=========================================================
Package root for the Trip Planner application.

    from app import create_app
    app = create_app()
"""

__version__ = "1.0.0"
__title__   = "Trip Planner"
__author__  = "Trip Planner Team"


def create_app():
    from app.main import build_app
    return build_app()


__all__ = ["create_app", "__version__", "__title__"]