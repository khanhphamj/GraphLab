from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import (
    auth_router, users_router, labs_router, lab_members_router,
    brainstorm_sessions_router, research_keywords_router,
    kg_schemas_router, neo4j_connections_router
)
from app.utils.exceptions import (
    GraphLabException, AuthenticationError, AuthorizationError,
    ValidationError, NotFoundError, ConflictError, RateLimitError
)

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

# Exception handlers
@app.exception_handler(GraphLabException)
async def graphlab_exception_handler(request: Request, exc: GraphLabException):
    status_code_map = {
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "NOT_FOUND_ERROR": status.HTTP_404_NOT_FOUND,
        "CONFLICT_ERROR": status.HTTP_409_CONFLICT,
        "RATE_LIMIT_ERROR": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    
    status_code = status_code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "detail": str(exc)
        }
    )


# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(labs_router)
app.include_router(lab_members_router)
app.include_router(brainstorm_sessions_router)
app.include_router(research_keywords_router)
app.include_router(kg_schemas_router)
app.include_router(neo4j_connections_router)

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