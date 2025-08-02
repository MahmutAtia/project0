from fastapi import APIRouter
from langserve.server import add_routes
from .chains import chain_instance
from .prompts import (
    create_resume_prompt,
    job_desc_resume_prompt,
    ats_checker_prompt,
    ats_checker_no_job_desc_prompt,
)

from .website_prompts import (
    create_resume_website_bloks_prompt,
    edit_website_block_prompt,
)
from .docs_prompts import (
    cover_letter_prompt,
    recommendation_letter_prompt,
    motivation_letter_prompt,
    edit_docs_section_prompt,
)

router = APIRouter()


add_routes(
    router,
    chain_instance.build_chain(create_resume_prompt),
    path="/genereate_from_input",
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



add_routes(
    router,
    chain_instance.build_chain(job_desc_resume_prompt),
    path="/genereate_from_job_desc",
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


add_routes(
    router,
    chain_instance.build_chain(
        create_resume_website_bloks_prompt, model="gemini-2.5-flash"
    ),
    path="/create_resume_website_bloks",
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

add_routes(
    router,
    chain_instance.build_chain(edit_website_block_prompt),
    path="/edit_block",
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


add_routes(
    router,
    chain_instance.build_chain(ats_checker_prompt),
    path="/ats_checker",
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
add_routes(
    router,
    chain_instance.build_chain(ats_checker_no_job_desc_prompt),
    path="/ats_checker_no_job_desc",
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

