from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import summary, rolling, forecast

app = FastAPI(title="Asian Capital Markets Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summary.router,  prefix="/analytics", tags=["Analytics"])
app.include_router(rolling.router,  prefix="/analytics", tags=["Analytics"])
app.include_router(forecast.router, prefix="/analytics", tags=["Analytics"])

@app.get("/health")
def health():
    return {"status": "ok"}
