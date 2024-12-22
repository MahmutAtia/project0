from fastapi import APIRouter, HTTPException, status
from typing import List
from models.resumes import Resume
from db.mongodb import get_database

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.post("/", response_model=Resume, status_code=status.HTTP_201_CREATED)
async def create_resume(resume: Resume):
    try:
        # Get database instance
        db = await get_database()
        collection = db["resumes"]
        
        # Insert resume and get the inserted document
        resume_dict = resume.model_dump()
        result = await collection.insert_one(resume_dict)
        
        # Fetch and return the created resume
        created_resume = await collection.find_one({"_id": result.inserted_id})
        if created_resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        return Resume(**created_resume)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# ... other resume endpoints (GET, PUT, DELETE, etc.)
@router.get("/", response_model=List[Resume])
async def get_all_resumes():
    db = await get_database()
    collection = db["resumes"]
    resumes = []
    async for doc in collection.find():
        resumes.append(Resume(**doc))
    return resumes