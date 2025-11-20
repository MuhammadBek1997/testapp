from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import user_routes, file_routes
import os

app = FastAPI()

cors = os.getenv("CORS_ORIGINS")
origins = [o.strip() for o in (cors.split(",") if cors else [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8081",
])]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router)
app.include_router(file_routes.router)

@app.get("/")
def health():
    return {"status": "ok"}