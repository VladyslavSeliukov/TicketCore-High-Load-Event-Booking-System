from fastapi import FastAPI, Request
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse

from src.core.config import settings
from src.api.v1 import tickets, events

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f'{settings.API_V1_STR}/openapi.json'
)

app.include_router(tickets.router, prefix=f'{settings.API_V1_STR}/tickets', tags=['Tickets'])
app.include_router(events.router, prefix=f'{settings.API_V1_STR}/events', tags=['Events'])

@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            'detail' : 'Data conflict occurred',
            'type' : 'IntegrityError'
        }
    )

@app.get('/', tags=['System'])
async def main():
    return {
        'status' : 'healthy',
        'app' : settings.PROJECT_NAME,
        'env' : settings.ENVIRONMENT
    }