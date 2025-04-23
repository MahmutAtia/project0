from fastapi import APIRouter
from langserve.server import add_routes
from .chains import chain_instance
from .prompts import ( 
                      create_resume_prompt, edit_resume_section_prompt ,job_desc_resume_prompt, create_resume_website_prompt, create_resume_website_bloks_prompt
                      ,edit_website_block_prompt,create_document_prompt,ats_checker_prompt,ats_checker_no_job_desc_prompt
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
    chain_instance.build_chain(edit_resume_section_prompt),
    path="/edit_section",
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
    chain_instance.build_chain(create_resume_website_prompt),
    path="/create_resume_website",
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
    chain_instance.build_chain(create_resume_website_bloks_prompt),
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
    chain_instance.build_chain(create_document_prompt),
    path="/create_document",
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