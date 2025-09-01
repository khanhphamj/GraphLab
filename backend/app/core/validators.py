from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

def validate_email(email: str) -> None:
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError(f"Invalid email: {email}")
    
def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    # Thêm complexity checks
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")

def validate_name(name: str) -> None:
    if len(name) < 1 or len(name) > 64:
        raise ValueError("Name must be at least 1 character long and less than 64 characters")

def validate_description(description: str) -> None:
    if len(description) == 0 or len(description) > 255:
        raise ValueError("Description must be less than 255 characters")


    
