import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from db.mongodb import MongoDB
from models.resumes import Resume
from dotenv import load_dotenv

load_dotenv()

# routers
from features.creator.routes import router as creator_router
from features.user_data.resume import router as resume_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Proj0 API Server",
        description="API server using Langchain's Runnable interfaces"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(creator_router)
    app.include_router(resume_router)
    
    return app

app = create_app()

# Initialize MongoDB instance
MONGOURI = os.environ.get("MONGO_DETAILS")
MONGODB = os.environ.get("MONGO_DB_NAME")
db = MongoDB(mongo_url=MONGOURI, db_name=MONGODB)

@app.on_event("startup")
async def startup_event():
    await db.initialize()
    

@app.on_event("shutdown")
async def shutdown_event():
    await db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)