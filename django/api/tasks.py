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
from celery.exceptions import Ignore # Import Ignore for non-retryable errors
from django.core.files.base import ContentFile # To potentially save file later
import base64 # To encode PDF bytes for JSON result backend
from django.core.cache import cache # <-- ADD THIS LINE


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
def generate_and_save_resume_task(self, user_id, input_text, job_description, language, ats_result=None):
    """
    Celery task to generate a resume using an AI service and save it to the database.
    """
    try:
        # Prepare input for the generation service
        input_data_generate = {
            "input": {
                'input_text': input_text,
                'job_description': job_description,
                'language': language,
                'ats_result': ats_result,
            }
        }
        if job_description == "":
            ai_service_url_generate = os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
        else:
            ai_service_url_generate = os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"

        # Call the generation service
        logger.info(f"Celery task: Calling AI service for resume generation for user_id: {user_id}")
        response_generate = requests.post(ai_service_url_generate, json=input_data_generate, timeout=300)
        response_generate.raise_for_status()

        # Process the response
        generated_resume_yaml_str = response_generate.json().get("output")
        if not generated_resume_yaml_str:
            raise ValueError("AI service did not return generated resume YAML.")

        # Parse the YAML
        generated_resume_data = yaml.safe_load(generated_resume_yaml_str)
        if not generated_resume_data:
            raise ValueError("Failed to parse generated resume YAML.")

        # Convert date objects in the parsed data
        generated_resume_data_serializable = convert_dates_to_strings(generated_resume_data)
        
        # Extract data (handle potential missing keys gracefully)
        title = generated_resume_data_serializable.get("title")
        description = generated_resume_data_serializable.get("description")
        icon = generated_resume_data_serializable.get("primeicon")
        resume_data = generated_resume_data_serializable.get("resume")
        about = generated_resume_data_serializable.get("about_candidate")

        # Find the user
        user = User.objects.filter(id=user_id).first()
        if not user:
            logger.error(f"Celery task error: User with id {user_id} not found.")
            raise self.retry(exc=User.DoesNotExist(f"User {user_id} not found"))

        # Save the generated resume data
        logger.info(f"Celery task: Saving generated resume for user_id: {user_id}")
        new_resume = Resume.objects.create(
                user=user,
                resume=resume_data,
                title=title,
                about=about,
                icon=icon,
                description=description
            )
        logger.info(f"Celery task: Successfully saved resume with id {new_resume.id} for user_id: {user_id}")
        return {"status": "SUCCESS", "resume_id": new_resume.id}


    except requests.exceptions.Timeout as exc:
        logger.warning(f"Celery task timeout calling AI service for user_id {user_id}: {exc}")
        raise self.retry(exc=exc)
    except requests.exceptions.RequestException as exc:
        logger.error(f"Celery task error calling AI service for user_id {user_id}: {exc}")
        if exc.response is not None and 400 <= exc.response.status_code < 500:
            logger.error(f"Non-retryable client error from AI service: {exc.response.status_code}")
            return None
        raise self.retry(exc=exc)
    except (yaml.YAMLError, ValueError) as e:
        logger.error(f"Celery task error processing YAML/data for user_id {user_id}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Celery task error (Unknown) for user_id {user_id}: {e}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for task processing user_id {user_id}.")
            return None



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_resume_data_task(self, input_text, job_description, language, ats_result=None):
    """
    Celery task to generate resume data using an AI service.
    Stores the result temporarily in cache.
    """
    task_id = self.request.id
    try:
        logger.info(f"Starting resume data generation task {task_id}")
        # Prepare input for the generation service
        input_data_generate = {
            "input": {
                'input_text': input_text,
                'job_description': job_description,
                'language': language,
                'ats_result': ats_result, # Pass ATS result if available
            }
        }
        # Determine AI service URL based on job description presence
        if not job_description:
            ai_service_url_generate = os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
        else:
            ai_service_url_generate = os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"

        # Call the generation service
        logger.info(f"Task {task_id}: Calling AI service for resume generation at {ai_service_url_generate}")
        response_generate = requests.post(ai_service_url_generate, json=input_data_generate, timeout=300) # Adjust timeout as needed
        response_generate.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Process the response
        generated_resume_yaml_str = response_generate.json().get("output")
        if not generated_resume_yaml_str:
            logger.error(f"Task {task_id}: AI service did not return generated resume YAML.")
            raise ValueError("AI service did not return generated resume YAML.")

        # Parse the YAML
        generated_resume_data = yaml.safe_load(generated_resume_yaml_str)
        if not generated_resume_data:
            logger.error(f"Task {task_id}: Failed to parse generated resume YAML.")
            raise ValueError("Failed to parse generated resume YAML.")

        # Convert date objects for JSON serialization compatibility
        generated_resume_data_serializable = convert_dates_to_strings(generated_resume_data)

        # Store the generated data in cache with the task_id as key
        # Set a reasonable timeout (e.g., 1 hour = 3600 seconds)
        cache_key = f"generated_resume_data_{task_id}"
        cache.set(cache_key, generated_resume_data_serializable, timeout=3600)
        logger.info(f"Task {task_id}: Successfully generated and cached resume data under key {cache_key}")

        # Return success status and indicate data is in cache
        return {"status": "SUCCESS", "data_location": "cache", "cache_key": cache_key}

    # --- Keep existing exception handling, but modify return values/logging ---
    except requests.exceptions.Timeout as exc:
        logger.warning(f"Task {task_id} timeout calling AI service: {exc}")
        raise self.retry(exc=exc) # Retry on timeout
    except requests.exceptions.RequestException as exc:
        logger.error(f"Task {task_id} error calling AI service: {exc}")
        # Don't retry client errors (4xx), fail the task
        if exc.response is not None and 400 <= exc.response.status_code < 500:
            logger.error(f"Task {task_id}: Non-retryable client error from AI service: {exc.response.status_code}")
            # Return None or raise specific exception to mark failure clearly
            raise ValueError(f"AI Service Client Error: {exc.response.status_code}")
        raise self.retry(exc=exc) # Retry on other request exceptions (e.g., connection errors)
    except (yaml.YAMLError, ValueError, KeyError) as e: # Added KeyError
        logger.error(f"Task {task_id} error processing YAML/data: {e}")
        # Do not retry data processing errors, fail the task
        raise ValueError(f"Data Processing Error: {e}")
    except Exception as e:
        logger.exception(f"Task {task_id} unexpected error: {e}")
        try:
            # Retry on unknown errors, up to max_retries
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Task {task_id}: Max retries exceeded.")
            # Fail the task after max retries
            raise e # Re-raise the original exception




@shared_task(bind=True, max_retries=2, default_retry_delay=30) # Adjust retries/delay as needed
def generate_pdf_task(self, resume_data, template_theme, chosen_theme, task_id_from_view=None):
    """
    Celery task to generate a PDF from resume data in the background.
    Returns base64 encoded PDF data on success.
    """
    task_id = self.request.id or task_id_from_view # Use Celery's ID if available
    logger.info(f"Starting PDF generation task {task_id}...")
    try:
        # Generate PDF bytes using the existing utility function
        pdf_bytes = generate_pdf_from_resume_data(resume_data, template_theme, chosen_theme)

        if pdf_bytes:
            logger.info(f"PDF generated successfully for task {task_id}. Encoding...")
            # Encode the PDF bytes as base64 to store in result backend
            # WARNING: Large PDFs might exceed result backend size limits (e.g., Redis).
            # Consider saving to a file/database/cloud storage and returning a URL/ID instead for large files.
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            logger.info(f"PDF encoded for task {task_id}. Task successful.")
            return {
                'status': 'SUCCESS',
                'pdf_base64': pdf_base64,
                'filename': f"generated_resume_{task_id}.pdf" # Suggest a filename
            }
        else:
            # Handle case where PDF generation function returned None without an exception
            logger.error(f"PDF generation failed for task {task_id}: generate_pdf_from_resume_data returned None.")
            # Use Ignore() to prevent retries for non-exception failures if desired
            raise Ignore("PDF generation function returned None.")
            # Or raise a ValueError to allow retries:
            # raise ValueError("PDF generation function returned None.")

    except Exception as e:
        logger.exception(f"Error during PDF generation task {task_id}: {e}")
        # Retry the task based on max_retries, default_retry_delay
        # Celery's default behavior on unhandled exceptions is to retry if bind=True
        raise self.retry(exc=e)
