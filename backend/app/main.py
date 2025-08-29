from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.session import SessionLocal
from app.routers import user

app = FastAPI(title="GraphLap API", description="API for GraphLap", version="1.0.0")

app.include_router(user.router, prefix="/users", tags=["users"])

@app.get("/health")
def health_check():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            return JSONResponse(content={f"Health check passed"}, status_code=status.HTTP_200_OK)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Internal server error: {str(e)}")

