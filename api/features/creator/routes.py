from fastapi import APIRouter
from langserve.server import add_routes
from .chains import chain_instance
from .prompts import create_resume_prompt
router = APIRouter()


add_routes(
    router,
    chain_instance.build_chain(create_resume_prompt),
    path="/create_resume",
    disabled_endpoints=[
        "stream_events",
        "stream_log",
        "batch",
        "playground",
        "config_hashes",
        "input_schema",
        "output_schema",
        "config_schema",
        "token_feedback",
    ],
)
