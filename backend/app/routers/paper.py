from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.paper import PaperCreate, PaperUpdate, PaperResponse
from app.services.paper import create_paper, get_paper, get_papers, update_paper, delete_paper, PaperNotFoundError, PaperAlreadyExistsError
from app.services.lab import get_user_lab
from app.db.deps import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.utils.slug import is_valid_slug

router = APIRouter()

# ============================================================================
# PAPER MANAGEMENT ENDPOINTS - SECURE
# ============================================================================

@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper_route(paper_in: PaperCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new paper - AUTHENTICATED.
    """
    try:
        lab = get_user_lab(db, paper_in.lab_slug, current_user.id)
        paper_in.lab_id = lab.id
        return create_paper(db, paper_in)
    except PaperAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")

@router.get("/{lab_slug}/{entry_id}", response_model=PaperResponse, status_code=status.HTTP_200_OK)
def get_paper_route(lab_slug: str, entry_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get a paper by lab slug and entry id - AUTHENTICATED.
    """
    try:
        lab = get_user_lab(db, lab_slug, current_user.id)
        return get_paper(db, lab.id, entry_id)
    except PaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")

@router.get("/{lab_slug}", response_model=List[PaperResponse], status_code=status.HTTP_200_OK)
def get_papers_route(lab_slug: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all papers by lab slug - AUTHENTICATED.
    """
    try:
        lab = get_user_lab(db, lab_slug, current_user.id)
        return get_papers(db, lab.id)
    except PaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")

@router.put("/{lab_slug}/{entry_id}", response_model=PaperResponse, status_code=status.HTTP_200_OK)
def update_paper_route(lab_slug: str, entry_id: str, paper_in: PaperUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update a paper by lab slug and entry id - AUTHENTICATED.
    """
    try:
        lab = get_user_lab(db, lab_slug, current_user.id)
        return update_paper(db, lab.id, entry_id, paper_in)
    except PaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")

@router.delete("/{lab_slug}/{entry_id}", status_code=status.HTTP_200_OK)
def delete_paper_route(lab_slug: str, entry_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Validate slug format
        if not is_valid_slug(lab_slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid lab slug format. Use lowercase letters, numbers, and hyphens only."
            )
        
        # Convert slug to readable name
        # Find lab by name for current user
        lab = get_user_lab(db, lab_slug, current_user.id)
        try:
            return delete_paper(db, lab.id, entry_id)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error: {str(e)}")
    except PaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"Internal server error: {str(e)}")