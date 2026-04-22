import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import assets, optimizer, simulation, attribution

app = FastAPI(title="Folio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)
app.include_router(optimizer.router)
app.include_router(simulation.router)
app.include_router(attribution.router)


@app.get("/health")
def health():
    return {"status": "ok"}
