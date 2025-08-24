from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.session import SessionLocal

app = FastAPI()

@app.get("/health")
def health_check():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            return JSONResponse(content={"status": "ok"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)