from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    }