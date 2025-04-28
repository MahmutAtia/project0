import os
import requests
import yaml
import json
import logging
from celery import shared_task
from .models import Resume
from django.contrib.auth import get_user_model
from datetime import date

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
        response_generate = requests.post(ai_service_url_generate, json=input_data_generate, timeout=180)
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
        return new_resume.id

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
