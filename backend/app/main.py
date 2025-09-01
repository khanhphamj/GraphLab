from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, user, lab

app = FastAPI(
    title="GraphLab API",
    description="API for GraphLab platform",
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
    allow_credentials=True,      
    allow_methods=["*"],         # Allow all HTTP methods
    allow_headers=["*"],         # Allow all headers
)

# Include routers
app.include_router(auth, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(user, prefix="/api/v1/users", tags=["users"])
app.include_router(lab, prefix="/api/v1/labs", tags=["labs"])

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
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users", 
            "labs": "/api/v1/labs"
        }
    }