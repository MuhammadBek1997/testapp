from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import user_routes, file_routes
import os

app = FastAPI()

cors = os.getenv("CORS_ORIGINS")
origins = [o.strip() for o in (cors.split(",") if cors else [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
    "http://localhost:8081",
])]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router)
app.include_router(file_routes.router)

@app.get("/")
def health():
    return {"status": "ok"}