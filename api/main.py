from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware


# routers
from features.creator.routes import router as creator_router
from features.scraper.routes import router as scraper_router
from features.resumes.routes import router as resumes_router

# create the fastapi app

app = FastAPI(
    title="Proj0 API Server",
    description=" api server using Langchain's Runnable interfaces",
    middleware=[
        # Middleware to add a header to all responses
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
)


# include the routers

app.include_router(creator_router, prefix="/resumes", tags=["resumes"])
app.include_router(scraper_router, prefix="/scraper", tags=["scraper"])
app.include_router(resumes_router, prefix="/resumes-v2", tags=["resumes-v2"])
