from .auth import router as auth_router
from .user import router as user_router
from .lab import router as lab_router

# Export routers for main.py
auth = auth_router
user = user_router
lab = lab_router