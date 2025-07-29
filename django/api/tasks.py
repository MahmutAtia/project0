import os
import requests
import yaml
import json
import logging
from celery import shared_task
from .models import Resume
from django.contrib.auth import get_user_model
from datetime import date
from .utils import generate_pdf_from_resume_data
from celery.exceptions import Ignore  # Import Ignore for non-retryable errors
from django.core.files.base import ContentFile  # To potentially save file later
import base64  # To encode PDF bytes for JSON result backend
from django.core.cache import cache  # <-- ADD THIS LINE
from django.db import OperationalError  # Import potential DB errors if needed

logger = logging.getLogger(__name__)
User = get_user_model()


# Helper function to convert date objects to strings
def convert_dates_to_strings(obj):
    if isinstance(obj, dict):
        return {k: convert_dates_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates_to_strings(elem) for elem in obj]
    elif isinstance(obj, date):
        return obj.isoformat()  # Convert date to 'YYYY-MM-DD' string
    else:
        return obj


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_and_save_resume_task(
    self, user_id, input_text, job_description, language, ats_result=None
):
    """
    Celery task to generate a resume using an AI service and save it to the database.
    Retries only on specific transient errors (timeouts, connection errors, 5xx from AI).
    """
    task_id = self.request.id
    logger.info(
        f"Task {task_id}: generate_and_save_resume_task ENTERED for user_id: {user_id}."
    )  # Added user_id
    try:
        # Prepare input for the generation service
        input_data_generate = {
            "input": {
                "input_text": input_text,
                "job_description": job_description,
                "language": language,
                "ats_result": ats_result,
            }
        }
        if job_description == "":
            ai_service_url_generate = (
                os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
            )
        else:
            ai_service_url_generate = (
                os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"
            )

        # Call the generation service
        logger.info(
            f"Task {task_id}: Calling AI service for resume generation for user_id: {user_id}"
        )
        response_generate = requests.post(
            ai_service_url_generate, json=input_data_generate, timeout=300
        )
        response_generate.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Process the response
        generated_resume_yaml_str = response_generate.json().get("output")
        if not generated_resume_yaml_str:
            logger.error(
                f"Task {task_id}: AI service did not return generated resume YAML for user_id: {user_id}."
            )
            raise Ignore(
                "AI service did not return generated resume YAML."
            )  # Fail, don't retry

        # Parse the YAML
        generated_resume_data = yaml.safe_load(generated_resume_yaml_str)
        if not generated_resume_data:
            logger.error(
                f"Task {task_id}: Failed to parse generated resume YAML for user_id: {user_id}."
            )
            # Log the problematic YAML
            logger.error(
                f"Problematic YAML string for task {task_id}:\n---\n{generated_resume_yaml_str}\n---"
            )
            raise Ignore("Failed to parse generated resume YAML.")  # Fail, don't retry

        # Convert date objects in the parsed data
        generated_resume_data_serializable = convert_dates_to_strings(
            generated_resume_data
        )

        # Extract data (handle potential missing keys gracefully)
        title = generated_resume_data_serializable.get("title")
        description = generated_resume_data_serializable.get("description")
        icon = generated_resume_data_serializable.get("primeicon")
        resume_data = generated_resume_data_serializable.get("resume")
        about = generated_resume_data_serializable.get("about_candidate")
        job_search_keywords = generated_resume_data_serializable.get("job_search_keywords")

        # Find the user
        try:
            user = User.objects.get(
                id=user_id
            )  # Use get() for clarity, handle DoesNotExist
        except User.DoesNotExist:
            logger.error(f"Task {task_id} error: User with id {user_id} not found.")
            raise Ignore(f"User {user_id} not found.")  # Fail, don't retry

        # Save the generated resume data
        logger.info(f"Task {task_id}: Saving generated resume for user_id: {user_id}")
        new_resume = Resume.objects.create(
            user=user,
            resume=resume_data,
            title=title,
            about=about,
            icon=icon,
            description=description,
            job_search_keywords=job_search_keywords,
        )
        logger.info(
            f"Task {task_id}: Successfully saved resume with id {new_resume.id} for user_id: {user_id}"
        )
        return {"status": "SUCCESS", "resume_id": new_resume.id}

    # --- Specific, RETRYABLE Exceptions ---
    except requests.exceptions.Timeout as exc:
        logger.warning(
            f"Task {task_id}: Timeout calling AI service for user_id {user_id}: {exc}. Retrying..."
        )
        raise self.retry(exc=exc)  # Retry on timeout

    except requests.exceptions.RequestException as exc:
        # Retry only on non-4xx errors (e.g., connection errors, 5xx server errors from AI)
        if exc.response is not None and 400 <= exc.response.status_code < 500:
            logger.error(
                f"Task {task_id}: Non-retryable client error {exc.response.status_code} from AI service for user_id {user_id}: {exc}"
            )
            raise Ignore(
                f"AI Service Client Error: {exc.response.status_code}"
            )  # Fail, don't retry
        else:
            logger.warning(
                f"Task {task_id}: RequestException calling AI service for user_id {user_id}: {exc}. Retrying..."
            )
            raise self.retry(exc=exc)  # Retry on other connection/server errors

    # --- Specific, NON-RETRYABLE Exceptions (Caught by type) ---
    except (yaml.YAMLError, ValueError, KeyError) as e:
        logger.error(
            f"Task {task_id}: Data processing error (YAML/Value/Key) for user_id {user_id}: {e}"
        )
        if isinstance(e, yaml.YAMLError) and "generated_resume_yaml_str" in locals():
            logger.error(
                f"Problematic YAML string for task {task_id}:\n---\n{generated_resume_yaml_str}\n---"
            )
        raise Ignore(f"Data Processing Error: {e}")  # Fail, don't retry

    # --- Catch-all for UNEXPECTED errors (NON-RETRYABLE) ---
    except Exception as e:
        logger.exception(
            f"Task {task_id}: UNEXPECTED error for user_id {user_id}: {e}"
        )  # Use logger.exception to include traceback
        raise Ignore(
            f"Unexpected task error: {e}"
        )  # Fail immediately, don't retry code bugs


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_resume_data_task(
    self, input_text, job_description, language, ats_result=None
):
    """
    Celery task to generate resume data using an AI service.
    Stores the result temporarily in cache.
    Retries only on specific transient errors (timeouts, connection errors, 5xx from AI).
    """
    task_id = self.request.id
    logger.info(f"Task {task_id}: generate_resume_data_task ENTERED.")
    try:
        logger.info(f"Task {task_id}: Starting processing inside try block.")
        # Prepare input for the generation service
        input_data_generate = {
            "input": {
                "input_text": input_text,
                "job_description": job_description,
                "language": language,
                "ats_result": ats_result,  # Pass ATS result if available
            }
        }
        # Determine AI service URL based on job description presence
        if not job_description:
            ai_service_url_generate = (
                os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
            )
        else:
            ai_service_url_generate = (
                os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"
            )

        # Call the generation service
        logger.info(
            f"Task {task_id}: Calling AI service for resume generation at {ai_service_url_generate}"
        )
        response_generate = requests.post(
            ai_service_url_generate, json=input_data_generate, timeout=300
        )  # Adjust timeout as needed
        response_generate.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Process the response
        generated_resume_yaml_str = response_generate.json().get("output")
        if not generated_resume_yaml_str:
            logger.error(
                f"Task {task_id}: AI service did not return generated resume YAML."
            )
            raise Ignore(
                "AI service did not return generated resume YAML."
            )  # Fail, don't retry

        # Parse the YAML
        generated_resume_data = yaml.safe_load(generated_resume_yaml_str)
        if not generated_resume_data:
            logger.error(f"Task {task_id}: Failed to parse generated resume YAML.")
            # Log the problematic YAML
            logger.error(
                f"Problematic YAML string for task {task_id}:\n---\n{generated_resume_yaml_str}\n---"
            )
            raise Ignore("Failed to parse generated resume YAML.")  # Fail, don't retry

        # Convert date objects for JSON serialization compatibility
        generated_resume_data_serializable = convert_dates_to_strings(
            generated_resume_data
        )

        # Store the generated data in cache with the task_id as key
        cache_key = f"generated_resume_data_{task_id}"
        cache.set(cache_key, generated_resume_data_serializable, timeout=3600)
        logger.info(
            f"Task {task_id}: Successfully generated and cached resume data under key {cache_key}"
        )

        # Return success status and indicate data is in cache
        return {"status": "SUCCESS", "data_location": "cache", "cache_key": cache_key}

    # --- Specific, RETRYABLE Exceptions ---
    except requests.exceptions.Timeout as exc:
        logger.warning(
            f"Task {task_id}: Timeout calling AI service: {exc}. Retrying..."
        )
        raise self.retry(exc=exc)  # Retry on timeout

    except requests.exceptions.RequestException as exc:
        # Retry only on non-4xx errors (e.g., connection errors, 5xx server errors from AI)
        if exc.response is not None and 400 <= exc.response.status_code < 500:
            logger.error(
                f"Task {task_id}: Non-retryable client error {exc.response.status_code} from AI service: {exc}"
            )
            raise Ignore(
                f"AI Service Client Error: {exc.response.status_code}"
            )  # Fail, don't retry
        else:
            logger.warning(
                f"Task {task_id}: RequestException calling AI service: {exc}. Retrying..."
            )
            raise self.retry(exc=exc)  # Retry on other connection/server errors

    # --- Specific, NON-RETRYABLE Exceptions (Caught by type) ---
    except (yaml.YAMLError, ValueError, KeyError) as e:
        logger.error(f"Task {task_id}: Data processing error (YAML/Value/Key): {e}")
        if isinstance(e, yaml.YAMLError) and "generated_resume_yaml_str" in locals():
            logger.error(
                f"Problematic YAML string for task {task_id}:\n---\n{generated_resume_yaml_str}\n---"
            )
        raise Ignore(f"Data Processing Error: {e}")  # Fail, don't retry

    # --- Catch-all for UNEXPECTED errors (NON-RETRYABLE) ---
    except Exception as e:
        logger.exception(
            f"Task {task_id}: UNEXPECTED error: {e}"
        )  # Use logger.exception to include traceback
        raise Ignore(
            f"Unexpected task error: {e}"
        )  # Fail immediately, don't retry code bugs


@shared_task(
    bind=True, max_retries=2, default_retry_delay=30
)  # Adjust retries/delay as needed
def generate_pdf_task(
    self, resume_data, template_theme, chosen_theme, task_id_from_view=None
):
    """
    Celery task to generate a PDF from resume data in the background.
    Returns base64 encoded PDF data on success.
    """
    task_id = self.request.id or task_id_from_view  # Use Celery's ID if available
    logger.info(f"Starting PDF generation task {task_id}...")
    try:
        # Generate PDF bytes using the existing utility function
        pdf_bytes = generate_pdf_from_resume_data(
            resume_data, template_theme, chosen_theme
        )

        if pdf_bytes:
            logger.info(f"PDF generated successfully for task {task_id}. Encoding...")
            # Encode the PDF bytes as base64 to store in result backend
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            logger.info(f"PDF encoded for task {task_id}. Task successful.")
            return {
                "status": "SUCCESS",
                "pdf_base64": pdf_base64,
                "filename": f"generated_resume_{task_id}.pdf",  # Suggest a filename
            }
        else:
            logger.error(
                f"PDF generation failed for task {task_id}: generate_pdf_from_resume_data returned None."
            )
            raise Ignore("PDF generation function returned None.")

    except Exception as e:
        logger.exception(f"Error during PDF generation task {task_id}: {e}")
        raise self.retry(exc=e)
