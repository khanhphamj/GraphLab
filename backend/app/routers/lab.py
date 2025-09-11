import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.lab import LabCreate, LabUpdate, LabResponse
from app.services.lab import create_lab, get_lab, get_lab_model, get_user_labs, update_lab, delete_lab, LabNotFoundError, LabNameAlreadyExistsError
from app.db.deps import get_db
from app.models.lab import Lab
from app.models.user import User
from app.services.auth import get_current_user
from app.utils.slug import is_valid_slug, slug_to_name
from sqlalchemy import and_, or_

router = APIRouter()

# ============================================================================
# LAB MANAGEMENT ENDPOINTS - SECURE
# ============================================================================

@router.post("/", response_model=LabResponse, status_code=status.HTTP_201_CREATED)
def create_lab_route(lab_in: LabCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new lab - AUTHENTICATED.
    """
    try:
        lab_in.owner_id = current_user.id
        return create_lab(db, lab_in)
    except LabNameAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}")
    
@router.get("/{lab_slug}", response_model=LabResponse, status_code=status.HTTP_200_OK)
def get_lab_route(lab_slug: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Validate slug format
        if not is_valid_slug(lab_slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid lab slug format. Use lowercase letters, numbers, and hyphens only."
            )
        
        # Convert slug to readable name
        lab_name = slug_to_name(lab_slug)
        
        # Find lab by name for current user
        lab = db.query(Lab).filter(
            and_(
                Lab.owner_id == current_user.id,
                Lab.deleted_at.is_(None),
                or_(
                    Lab.name == lab_name,  # Exact match
                    Lab.name.ilike(lab_name.replace(' ', '%'))  # Fuzzy match
                )
            )
        ).first()
        
        if not lab:
            raise LabNotFoundError(lab_slug, current_user.id)
        
        return LabResponse.model_validate(lab)
        
    except LabNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Lab with slug '{lab_slug}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/", response_model=List[LabResponse], status_code=status.HTTP_200_OK)
def get_user_labs_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        labs = get_user_labs(db, current_user.id)
        return labs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}"
        )

@router.put("/{lab_slug}", response_model=LabResponse, status_code=status.HTTP_200_OK)
def update_lab_route(
    lab_slug: str,
    lab_in: LabUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate slug format
        if not is_valid_slug(lab_slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid lab slug format. Use lowercase letters, numbers, and hyphens only."
            )
        
        # Convert slug to readable name
        lab_name = slug_to_name(lab_slug)
        
        # Find lab by name for current user
        lab = db.query(Lab).filter(
            and_(
                Lab.owner_id == current_user.id,
                Lab.deleted_at.is_(None),
                or_(
                    Lab.name == lab_name,
                    Lab.name.ilike(lab_name.replace(' ', '%'))
                )
            )
        ).first()
        
        if not lab:
            raise LabNotFoundError(lab_slug, current_user.id)
        
        # Check for name conflicts if name is being updated
        if lab_in.name and lab_in.name != lab.name:
            existing_lab = db.query(Lab).filter(
                and_(
                    Lab.owner_id == current_user.id,
                    Lab.name == lab_in.name,
                    Lab.deleted_at.is_(None)
                )
            ).first()
            if existing_lab:
                raise LabNameAlreadyExistsError(lab_in.name, current_user.id)
        try:
            return update_lab(db, lab.id, lab_in)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}")
    except LabNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))

@router.delete("/{lab_slug}", status_code=status.HTTP_200_OK)
def delete_lab_route(lab_slug: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Validate slug format
        if not is_valid_slug(lab_slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid lab slug format. Use lowercase letters, numbers, and hyphens only."
            )
        # Convert slug to readable name
        lab_name = slug_to_name(lab_slug)
        # Find lab by name for current user
        lab = db.query(Lab).filter(
            and_(
                Lab.owner_id == current_user.id,
                Lab.deleted_at.is_(None),
                or_(
                    Lab.name == lab_name,
                    Lab.name.ilike(lab_name.replace(' ', '%'))
                )
            )
        ).first()
        if not lab:
            raise LabNotFoundError(lab_slug, current_user.id)
        try:
            return delete_lab(db, lab.id)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}")
    except LabNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")