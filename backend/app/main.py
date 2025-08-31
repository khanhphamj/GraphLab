from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, user

app = FastAPI(
    title="GraphLab API",
    description="Authentication & User Management API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend development
        "http://localhost:8080",  # Alternative frontend port
        "https://yourdomain.com", # Production domain
    ],
    allow_credentials=True,      # Cho phép gửi cookies/authorization
    allow_methods=["*"],         # Cho phép tất cả HTTP methods
    allow_headers=["*"],         # Cho phép tất cả headers
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")  # /api/v1/auth/*
app.include_router(user.router, prefix="/api/v1/users", tags=["users"])

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "GraphLab API"}

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Welcome to GraphLab API",
        "docs": "/docs",
        "version": "1.0.0"
    }