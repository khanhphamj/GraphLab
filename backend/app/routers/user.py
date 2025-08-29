import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import create_user, get_user, update_user, delete_user, EmailAlreadyExistsError,  UserNotFoundError

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_route(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, user_in)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Internal server error: {str(e)}")

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_route(user_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return get_user(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Internal server error: {str(e)}")

@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user_route(user_id: uuid.UUID, user_in: UserUpdate, db: Session = Depends(get_db)):
    try:
        return update_user(db, user_id, user_in)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=str(e))
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Internal server error: {str(e)}")

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)    
def delete_user_route(user_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        delete_user(db, user_id)
        return {"message": f"User {user_id} deleted successfully"}
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Internal server error: {str(e)}")

