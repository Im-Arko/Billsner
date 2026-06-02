from fastapi import APIRouter

from app.api.v1 import ai, auth, bills, expenses, reports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(bills.router)
api_router.include_router(expenses.router)
api_router.include_router(ai.router)
api_router.include_router(reports.router)
