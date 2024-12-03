from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware




# routers


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

# include routers
