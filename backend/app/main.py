from fastapi import FastAPI

from app.routes import complaints, meta, stats, system

app = FastAPI(title="CivicPulse API")

app.include_router(system.router)
app.include_router(complaints.router)
app.include_router(stats.router)
app.include_router(meta.router)