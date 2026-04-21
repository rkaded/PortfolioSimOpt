from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import assets, optimizer, simulation, attribution

app = FastAPI(title="Portfolio Intelligence Tool", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
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
