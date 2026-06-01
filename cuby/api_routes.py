from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from cuby.database import get_db
from cuby import models, schemas
from AI_logic_app import AI_logic

router = APIRouter(prefix="/api", tags=["ai"])

@router.post("/start_ai", response_model=schemas.AIStartResponse)
async def start_ai(db: Session = Depends(get_db)):
    """Start the AI assistant"""
    try:
        AI_logic.startup()
        return {"status": "success", "message": "CUBY started successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CUBY STOPPED: {str(e)}"
        )

@router.get("/queries", response_model=list[schemas.CubyQueryResponse])
async def get_queries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all saved queries"""
    queries = db.query(models.CubyQueries).offset(skip).limit(limit).all()
    return queries

@router.get("/queries/{query_id}", response_model=schemas.CubyQueryResponse)
async def get_query(query_id: int, db: Session = Depends(get_db)):
    """Get a specific query by ID"""
    query = db.query(models.CubyQueries).filter(models.CubyQueries.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    return query

@router.post("/queries", response_model=schemas.CubyQueryResponse)
async def create_query(query: schemas.CubyQueryCreate, db: Session = Depends(get_db)):
    """Save a new query and answer"""
    db_query = models.CubyQueries(query=query.query, answers=query.answers)
    db.add(db_query)
    db.commit()
    db.refresh(db_query)
    return db_query

@router.put("/queries/{query_id}", response_model=schemas.CubyQueryResponse)
async def update_query(
    query_id: int,
    query_update: schemas.CubyQueryUpdate,
    db: Session = Depends(get_db)
):
    """Update a query and its answers"""
    db_query = db.query(models.CubyQueries).filter(models.CubyQueries.id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    if query_update.query is not None:
        db_query.query = query_update.query
    if query_update.answers is not None:
        db_query.answers = query_update.answers
    
    db.commit()
    db.refresh(db_query)
    return db_query

@router.delete("/queries/{query_id}")
async def delete_query(query_id: int, db: Session = Depends(get_db)):
    """Delete a query"""
    db_query = db.query(models.CubyQueries).filter(models.CubyQueries.id == query_id).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db.delete(db_query)
    db.commit()
    return {"message": "Query deleted successfully"}
