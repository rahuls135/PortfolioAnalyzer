from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database import engine, Base
import models  # Import your models

app = FastAPI()

# Allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Portfolio Analyzer API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/setup-db")
def setup_database():
    Base.metadata.create_all(bind=engine)
    return {"message": "Database tables created successfully"}
