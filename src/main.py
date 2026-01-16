from fastapi import FastAPI
from src.core.config import settings
from src.api.v1 import tickets
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f'{settings.API_V1_STR}/openapi.json'
)

app.include_router(tickets.router, prefix=f'{settings.API_V1_STR}/tickets', tags=['Tickets'])

@app.get('/')
async def main():
    return {
        'status' : 'healthy',
        'app' : settings.PROJECT_NAME,
        'env' : 'dev'
    }