"""
Initialize API routers package
"""
from src.api.jobs import router as jobs_router
from src.api.printers import router as printers_router
# Queue router imported separately due to variable name conflict

__all__ = ['jobs_router', 'printers_router']

__all__ = []
