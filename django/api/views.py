from rest_framework import generics, permissions, status
from .models import Resume, GeneratedWebsite, GeneratedDocument
from .serializers import ResumeSerializer, UserProfileSerializer
from django.http import Http404
from .utils import (
    cleanup_old_sessions,
    extract_text_from_file,
    generate_pdf_from_resume_data,
    generate_html_from_yaml,
    parse_custom_format,
    format_data_to_ordered_text,
    generate_docx_from_template,
)
from rest_framework.response import Response
from django.contrib.auth.models import User
import requests  # For calling the AI service
from rest_framework.decorators import (
    api_view,
    permission_classes,
)  # from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import (
    StreamingHttpResponse,
    FileResponse,
    HttpResponse,
    JsonResponse,
    HttpResponseServerError,
)
from datetime import datetime  # Import datetime class directly
import textwrap
import json
import yaml
import os
import time
import uuid
import io

from .tasks import generate_resume_data_task  # Import the Celery task
from asgiref.sync import async_to_sync

# clerey
from celery import states  # Import states
from celery.result import AsyncResult

import httpx  # Add httpx for async requests
from asgiref.sync import sync_to_async  # For wrapping sync code if needed

from rest_framework import permissions
from django.core.cache import cache

from plans.decorators import require_feature

ORDER_MAP = {
    "resume": [
        "personal_information",
        "summary",
        "objective",
        "experience",
        "education",
        "skills",
        "projects",
        "awards_and_recognition",
        "Volunteer_and_social_activities",
        "certifications",
        "languages",
        "interests",
        "references",
        "publications",
        "courses",
        "conferences",
        "speaking_engagements",
        "patents",
        "professional_memberships",
        "military_service",
        "teaching_experience",
        "research_experience",
    ]
    # No order defined for keys within "personal_information", "experience" items, etc.
    # They will be printed in their natural dictionary order.
}


def file_iterator(file_handle, chunk_size=8192):
    """Helper function to iterate over a file-like object in chunks."""
    while True:
        chunk = file_handle.read(chunk_size)
        if not chunk:
            break
        yield chunk


FRONTEND_BASE_URL = "http://localhost:8000"  # settings.FRONTEND_BASE_URL
generate_pdf_from_resume_data


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the resumes
        for the currently authenticated user.
        It also prefetches related documents and website
        to optimize queries for the serializer's SerializerMethodFields.
        """
        user = self.request.user
        return Resume.objects.filter(user=user).prefetch_related(
            "generated_documents",  # Related name from Resume to GeneratedDocument
            "personal_website",  # Related name from Resume to GeneratedWebsite (OneToOne)
        )

    def perform_create(self, serializer):
        """
        Associate the resume with the logged-in user upon creation.
        """
        serializer.save(user=self.request.user)


class ResumeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_object(self):
        """
        Returns the object the view is displaying.
        Ensures the resume belongs to the current user.
        """
        resume_id = self.kwargs.get(self.lookup_field)
        resume = get_object_or_404(Resume, pk=resume_id, user=self.request.user)
        return resume

    def update(self, request, *args, **kwargs):
        """
        Update method that handles both PUT and PATCH.
        Most commonly used to update just the resume JSON content.
        """
        try:
            resume = self.get_object()
            partial = request.method == "PATCH"

            # Use the serializer to validate and update the data
            serializer = self.get_serializer(resume, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)

        except Exception as e:
            logger.exception(
                f"Error updating resume {self.kwargs.get(self.lookup_field)}: {e}"
            )
            return Response(
                {"error": f"Error updating resume: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@require_feature("resume_generation")
def generate_resume(request):
    # Test Redis connection
    try:
        cache.set("test_key", "test_value")
        test_value = cache.get("test_key")
    except Exception as e:
        return Response({"error": "Redis connection failed"}, status=500)

    input_data = request.data
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
    response = requests.post(ai_service_url, json=input_data)

    if response.status_code == 200:
        try:
            generated_resume_yaml = response.json().get("output")
            generated_resume_data = yaml.safe_load(generated_resume_yaml)

            # Extract the data
            title = generated_resume_data.get("title")  # the title of the resume
            description = generated_resume_data.get(
                "description"
            )  # the description of the resume
            icon = generated_resume_data.get(
                "fontawesome_icon"
            )  # the icon of the resume
            job_search_keywords = generated_resume_data.get(
                "job_search_keywords"
            )  # the job search keywords of the resume

            resume_data = generated_resume_data.get("resume")  # the resume data
            about = generated_resume_data.get("about_candidate")  # the about of the resume

            if not request.user.is_authenticated:
                timestamp = int(time.time())
                session_key = f"temp_resume_{timestamp}"

                # Store directly in Redis cache
                cache_data = {
                    "data": resume_data,
                    "created_at": timestamp,
                }

                cache.set(session_key, json.dumps(cache_data), timeout=3600)

                # Verify storage
                stored_data = cache.get(session_key)
                # print(f"DEBUG: Stored in Redis - {stored_data}")

                response = Response(
                    {
                        "id": session_key,
                        "message": "Resume stored in Redis",
                    },
                    status=status.HTTP_201_CREATED,
                )

                return response

            else:  # the user is authenticated it will save the resume in the database

                # if this the first resume of the user it will set it as the default resume
                if not Resume.objects.filter(user=request.user).exists():
                    is_default = True
                else:
                    is_default = False

                resume = Resume.objects.create(
                    user=request.user,
                    resume=resume_data,
                    job_search_keywords=job_search_keywords,
                    is_default=is_default,
                    title=title,
                    about=about,
                    icon=icon,
                    description=description,
                )
                print(f"DEBUG: Resume saved - {resume}")
                return Response(
                    {
                        "id": resume.id,
                        "message": "Resume saved successfully",
                    },
                    status=status.HTTP_201_CREATED,
                )

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return Response(
                {"error": f"Invalid data received from AI service: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        return Response(response.json(), status=response.status_code)


@api_view(["POST"])
@require_feature("resume_generation")  # Add this decorator
def generate_from_job_desc(request):
    try:

        uploaded_file = request.FILES.get("resume")
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=400)

        text = extract_text_from_file(uploaded_file)

        form_data = json.loads(request.POST.get("formData", "{}"))

        input_data = {
            "input": {
                "input_text": text,
                "job_description": form_data.get("description") or "",
                "language": form_data.get("targetLanguage") or "en",
                "docs_instructions": "\n".join(
                    f"Write a {key} tailored to the job description"
                    for key, value in form_data.get("documentPreferences", {}).items()
                    if value
                ),
            }
        }

        ai_service_url = (
            os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"
        )

        response = requests.post(ai_service_url, json=input_data)

        if response.status_code == 200:
            try:
                generated_resume_yaml = response.json().get("output")
                generated_resume_data = yaml.safe_load(generated_resume_yaml)

                title = generated_resume_data.get("title")
                description = generated_resume_data.get("description")
                icon = generated_resume_data.get("fontawesome_icon")
                job_search_keywords = generated_resume_data.get("job_search_keywords")
                resume_data = generated_resume_data.get("resume")
                about = generated_resume_data.get("about")

                if not request.user.is_authenticated:
                    timestamp = int(time.time())
                    session_key = f"temp_resume_{timestamp}"
                    cache_data = {
                        "data": resume_data,
                        "created_at": timestamp,
                    }
                    cache.set(session_key, json.dumps(cache_data), timeout=3600)
                    return Response(
                        {
                            "id": session_key,
                            "message": "Resume stored in Redis",
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    is_default = not Resume.objects.filter(user=request.user).exists()
                    resume = Resume.objects.create(
                        user=request.user,
                        resume=resume_data,
                        job_search_keywords=job_search_keywords,
                        is_default=is_default,
                        title=title,
                        about=about,
                        icon=icon,
                        description=description,
                    )
                    return Response(
                        {
                            "id": resume.id,
                            "message": "Resume saved successfully",
                        },
                        status=status.HTTP_201_CREATED,
                    )
            except (json.JSONDecodeError, yaml.YAMLError) as e:
                return Response(
                    {"error": f"Invalid data received from AI service: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(response.json(), status=response.status_code)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


################################## genereate_pdf #######s#########################

@api_view(["POST"])
@require_feature("pdf_generation")
def generate_pdf(request):
    """
    API endpoint to trigger background PDF generation.
    Returns a task ID for status checking.
    """
    resume_id = request.data.get("resume_id")
    template = request.data.get("templateTheme", "default.html")
    chosen_theme = request.data.get("chosenTheme", "theme-default")
    scale = request.data.get("scale", "medium")
    show_icons = request.data.get("showIcons", False)
    show_avatar = request.data.get("showAvatar", False)
    font_family = request.data.get("fontFamily", None)  # Add font family parameter
    
    print(f"DEBUG: Received resume_id: {resume_id}, template: {template}, chosen_theme: {chosen_theme}, scale: {scale}, show_icons: {show_icons}, show_avatar: {show_avatar}, font_family: {font_family}")
    
    if not resume_id:
        return Response(
            {"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate parameters
    if scale not in ["small", "medium", "large"]:
        return Response(
            {"error": "scale must be one of: small, medium, large"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not isinstance(show_icons, bool):
        return Response(
            {"error": "showIcons must be a boolean"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    if not isinstance(show_avatar, bool):
        return Response(
            {"error": "showAvatar must be a boolean"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    try:
        resume = get_object_or_404(Resume, pk=resume_id, user=request.user)
        resume_data = resume.resume
        sections_sort = resume.sections_sort
        hidden_sections = resume.hidden_sections
        
        if not isinstance(resume_data, (dict, list)):
            logger.error(
                f"Resume data for ID {resume_id} is not a dict/list: {type(resume_data)}"
            )
            return Response(
                {"error": "Invalid resume data format."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Handle avatar inclusion based on FRONTEND CHOICE (showAvatar parameter)
        try:
            user_profile = UserProfile.get_or_create_profile(resume.user)
            
            # Use the frontend's showAvatar parameter, not the stored preference
            if user_profile.avatar and show_avatar:
                # Ensure resume_data structure exists
                if not resume_data:
                    resume_data = {}
                if 'personal_information' not in resume_data:
                    resume_data['personal_information'] = {}
                
                # Add avatar to personal_information section for PDF generation
                resume_data['personal_information']['avatar'] = user_profile.avatar
                logger.info(f"Avatar added to resume {resume_id} for PDF generation per frontend choice (size: ~{len(user_profile.avatar)//1024}KB)")
            elif user_profile.avatar and not show_avatar:
                # Remove avatar from resume_data if it exists (user chose to exclude it)
                if resume_data and 'personal_information' in resume_data and 'avatar' in resume_data['personal_information']:
                    del resume_data['personal_information']['avatar']
                logger.info(f"Avatar excluded from resume {resume_id} PDF generation per frontend choice")
            else:
                logger.debug(f"No avatar found for user {resume.user.username} or avatar disabled")
        except Exception as avatar_error:
            logger.warning(f"Could not process avatar for PDF resume {resume_id}: {avatar_error}")
            # Continue without avatar - don't fail the entire PDF generation

    except Http404:
        return Response(
            {"error": f"Resume with ID {resume_id} not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.exception(f"Error fetching resume data for PDF generation: {e}")
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Pass the showAvatar and fontFamily parameters to the PDF generation function
    pdf_data = generate_pdf_from_resume_data(
        resume_data=resume_data, 
        template_theme=template, 
        chosen_theme=chosen_theme,
        sections_sort=sections_sort,
        hidden_sections=hidden_sections,
        scale=scale,
        show_icons=show_icons,
        show_avatar=show_avatar,
        font_family=font_family  # Pass font family to PDF generation
    )
    
    # Handle PDF generation result
    if pdf_data:
        pdf_buffer = io.BytesIO(pdf_data)
        filename = f"generated_document_{resume_id}"

        response = StreamingHttpResponse(
            file_iterator(pdf_buffer),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = (
            f'inline; filename="{filename}"'
        )
        response["Content-Length"] = len(pdf_data)
        return response
    else:
        return HttpResponseServerError("Error generating PDF document.")


@api_view(["GET"])
def get_pdf_generation_status(request, task_id):
    """
    Checks the status of a PDF generation Celery task.
    If successful, returns base64 encoded PDF data.
    """
    logger.debug(f"Checking status for PDF task_id: {task_id}")
    result = AsyncResult(task_id)

    response_data = {"task_id": task_id, "status": result.status, "result": None}

    if result.successful():
        task_result = result.get()
        response_data["result"] = task_result  # Store the result (which might be None)

        # Check if task_result is not None before trying to access it
        if task_result is not None and isinstance(task_result, dict):
            # Task completed successfully and returned a dictionary as expected
            response_data["status"] = task_result.get(
                "status", "SUCCESS"
            )  # Update status from task result if available
            logger.info(f"PDF Task {task_id} completed successfully with result.")
        elif task_result is None:
            # Task completed successfully but returned None
            logger.warning(
                f"PDF Task {task_id} completed successfully but returned None."
            )
            # Keep status as SUCCESS, but result is None
            response_data["status"] = "SUCCESS"  # Explicitly set status
        else:
            # Task completed successfully but returned an unexpected type
            logger.warning(
                f"PDF Task {task_id} completed successfully but returned unexpected type: {type(task_result)}"
            )
            response_data["status"] = "SUCCESS"  # Explicitly set status

        # Return 200 OK with the result (which might be None or the expected dict)
        return Response(response_data, status=status.HTTP_200_OK)

    elif result.status in [states.PENDING, states.STARTED, states.RETRY]:
        # Task is still processing or waiting
        logger.debug(f"PDF Task {task_id} status: {result.status}")
        response_data["result"] = {"message": f"Task is currently {result.status}"}
        # Return 200 OK, status indicates it's not ready yet
        return Response(response_data, status=status.HTTP_200_OK)
    else:
        # Unknown state
        logger.warning(f"PDF Task {task_id} has unknown status: {result.status}")
        response_data["result"] = {
            "message": f"Task has an unknown status: {result.status}"
        }
        return Response(response_data, status=status.HTTP_200_OK)


############################# generate website resume #############################


@api_view(["POST"])
@require_feature("website_generation")
def generate_personal_website(request):
    """
    API endpoint to generate and save a personal website.
    """
    resume_id = request.data.get("resumeId")
    preferences = request.data.get("preferences", {})

    if not resume_id:
        return Response(
            {"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        resume_data = resume.resume

        # Note: We don't add base64 avatar to website generation as it would make HTML too large
        # Website generation uses a different approach for images
        try:
            user_profile = UserProfile.get_or_create_profile(resume.user)
            
            # Check if user wants to include avatar (for future website avatar feature)
            include_avatar = resume.should_include_avatar_in_pdf()
            
            if user_profile.avatar and include_avatar:
                logger.info(f"User has avatar and wants it included - website avatar feature could be implemented later")
            elif user_profile.avatar and not include_avatar:
                logger.info(f"Avatar excluded from resume {resume_id} website generation per user preference")
            else:
                logger.debug(f"No avatar found for user {resume.user.username}")
        except Exception as avatar_error:
            logger.warning(f"Could not process avatar preference for website {resume_id}: {avatar_error}")
            # Continue without avatar - don't fail the entire website generation

        # Check if a website has already been generated for this resume
        generated_website = GeneratedWebsite.objects.filter(resume=resume).first()
        if generated_website:
            # Website already exists, return the unique link

            return Response(
                {"website_uuid": generated_website.unique_id}, status=status.HTTP_200_OK
            )

    except Exception as e:
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Generate the personal website
    resume_yaml = yaml.dump(resume_data)
    preferences = yaml.dump(preferences)  # Convert preferences to YAML
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "create_resume_website/invoke"
    body = {"input": {"resume_yaml": resume_yaml, "preferences": preferences}}

    try:
        ai_response = requests.post(ai_service_url, json=body)
        ai_response.raise_for_status()
        generated_website_yaml = ai_response.json().get("output")
        generated_website_data = yaml.safe_load(generated_website_yaml)
        html_code = generated_website_data.get("html")
        css_code = generated_website_data.get("css")
        js_code = generated_website_data.get("js")

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Website</title>
    <style>
        {css_code}
    </style>
</head>
<body>
    {html_code}
    <script>
        {js_code}
    </script>
</body>
</html>"""

        # Save the generated website
        unique_id = str(uuid.uuid4())
        GeneratedWebsite.objects.create(
            resume=resume, unique_id=unique_id, html_content=full_html
        )

        # Return the unique link
        website_url = f"{FRONTEND_BASE_URL}/api/website/{unique_id}/"
        return Response({"website_url": website_url}, status=status.HTTP_201_CREATED)

    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Error communicating with AI service: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except (yaml.YAMLError, AttributeError) as e:
        return Response(
            {"error": f"Error processing AI service response: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@require_feature("website_generation")  # Add this decorator
def generate_personal_website_bloks(request):
    """
    API endpoint to generate and save a personal website using Bloks.
    """
    resume_id = request.data.get("resumeId")
    preferences = request.data.get("preferences", {})

    if not resume_id:
        return Response(
            {"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        resume_data = resume.resume

        # Note: We don't add base64 avatar to website generation as it would make HTML too large
        # Website generation uses a different approach for images
        try:
            user_profile = UserProfile.get_or_create_profile(resume.user)
            
            # Check if user wants to include avatar (for future website avatar feature)
            include_avatar = resume.should_include_avatar_in_pdf()
            
            if user_profile.avatar and include_avatar:
                logger.info(f"User has avatar and wants it included - website avatar feature could be implemented later")
            elif user_profile.avatar and not include_avatar:
                logger.info(f"Avatar excluded from resume {resume_id} website regeneration per user preference")
            else:
                logger.debug(f"No avatar found for user {resume.user.username}")
        except Exception as avatar_error:
            logger.warning(f"Could not process avatar preference for website {resume_id}: {avatar_error}")
            # Continue without avatar - don't fail the entire website generation

        # Check if a website has already been generated for this resume
        generated_website = GeneratedWebsite.objects.filter(resume=resume).first()
        if generated_website:
            # Website already exists, return the unique link
            return Response(
                {"website_uuid": generated_website.unique_id}, status=status.HTTP_200_OK
            )

    except Exception as e:
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Generate the personal website using Bloks
    resume_yaml = "\n".join(
        format_data_to_ordered_text(resume_data, "resume", ORDER_MAP)
    )
    ai_service_url = (
        os.environ.get("AI_SERVICE_URL") + "create_resume_website_bloks/invoke"
    )
    body = {"input": {"resume_yaml": resume_yaml, "preferences": preferences}}

    try:
        ai_response = requests.post(ai_service_url, json=body)
        ai_response.raise_for_status()
        generated_website_bloks = ai_response.json().get("output")
        generated_website_bloks_json = parse_custom_format(generated_website_bloks)

        # Save the generated website YAML
        unique_id = str(uuid.uuid4())
        GeneratedWebsite.objects.create(
            resume=resume,
            unique_id=unique_id,
            json_content=generated_website_bloks_json,
        )

        # Return the unique id
        return Response({"website_uuid": unique_id}, status=status.HTTP_201_CREATED)

    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Error communicating with AI service: {e}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except (yaml.YAMLError, AttributeError) as e:
        return Response(
            {"error": f"Error processing AI service response: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def get_website_yaml_json(request, resume_id):
    """
    API endpoint to serve the parsed YAML content for a given website ID (resume_id).
    """
    try:
        # Assuming unique_id in your model corresponds to the resume_id from frontend
        # Adjust lookup field if necessary (e.g., pk=resume_id)
        generated_website = get_object_or_404(GeneratedWebsite, unique_id=resume_id)

        data = generated_website.json_content

        # Return the parsed YAML (Python dict/list) as JSON
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        # Catch any other unexpected errors (e.g., database issues)
        print(f"An unexpected error occurred: {e}")  # Log the error
        return Response(
            {"error": "An internal server error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def serve_personal_website_yaml(request, unique_id):
    """
    API endpoint to serve a pre-generated personal website using Bloks.
    """
    try:
        generated_website = get_object_or_404(GeneratedWebsite, unique_id=unique_id)

        json_data = generated_website.json_content
        # Generate the HTML from the YAML data
        full_html = generate_html_from_yaml(json_data)
        return HttpResponse(full_html, content_type="text/html")
    except Exception as e:
        return Response(
            {"error": f"Website not found: {e}"}, status=status.HTTP_404_NOT_FOUND
        )


############################## Update yaml website content ##############################
@api_view(["PUT"])
def update_website_yaml(request, unique_id):
    """
    API endpoint to update the YAML content of a personal website.
    """
    try:
        generated_website = get_object_or_404(GeneratedWebsite, unique_id=unique_id)

        json_content = (
            request.data
        )  # the json content from the frontend has global and code_bloks

        # Update the YAML content in the database
        generated_website.json_content = json_content
        generated_website.save()

        return Response(
            {"message": "YAML content updated successfully"}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": f"Error updating website: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


############################### edit website block ###############################


@api_view(["POST"])
@require_feature("website_generation")  # Add this decorator
def edit_website_block(request):
    data = json.loads(request.body)
    resume_id = data.get("resumeId")
    current_name = data.get("blockName")
    current_html = data.get("currentHtml")
    current_css = data.get("currentCss")
    current_js = data.get("currentJs")
    prompt = data.get("prompt")
    artifacts = data.get("artifacts", [])

    if not all([resume_id, current_name, prompt]):
        print("Missing required parameters:", resume_id, current_name, prompt)
        return JsonResponse({"error": "Missing required parameters."}, status=400)

    # Call the AI service
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "edit_block/invoke"
    body = {
        "input": {
            "current_name": current_name,
            "current_html": textwrap.indent(
                current_html, "  "
            ),  # used to indent the html code
            "current_css": textwrap.indent(
                current_css, "  "
            ),  # used to indent the css code
            "current_js": textwrap.indent(
                current_js, "  "
            ),  # used to indent the js code
            "prompt": prompt,
            "artifacts": artifacts,
        }
    }

    response = requests.post(ai_service_url, json=body)
    if response.status_code == 200:
        try:
            generated_block_yaml = response.json().get("output")
            generated_block_data = yaml.safe_load(generated_block_yaml)
            html_code = generated_block_data.get("html")
            css_code = generated_block_data.get("css")
            js_code = generated_block_data.get("js")
            feedback_message = generated_block_data.get("feedback_message")

            return JsonResponse(
                {
                    "html": html_code,
                    "css": css_code,
                    "js": js_code,
                    "feedback_message": feedback_message,
                },
                status=200,
            )
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return JsonResponse(
                {"error": f"Invalid data received from AI service: {e}"}, status=500
            )
    else:
        return JsonResponse(
            {"error": "Error from AI service"}, status=response.status_code
        )


############################# Documents ##############################

@api_view(["POST"])
def create_document(request):
    """
    API endpoint to create a new generated document.
    """
    try:
        resume_id = request.data.get("resume_id")
        json_content = request.data.get("json_content")
        document_type = request.data.get("document_type", "")
 

        if not resume_id or not json_content or not document_type:
            return Response(
                {"error": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resume = get_object_or_404(Resume, pk=resume_id)
        unique_id = str(uuid.uuid4())


        generated_document = GeneratedDocument.objects.create(
            resume=resume,
            unique_id=unique_id,
            json_content=json_content,
            document_type=document_type,
        )
        return Response(
            {"message": "Document created successfully", "document_id": generated_document.unique_id},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response(
            {"error": f"Error creating document: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
@api_view(["GET"])
def get_document_bloks(request, document_id):
    """
    API endpoint to serve the generated document as a JSON response.
    """
    try:
        generated_document = get_object_or_404(GeneratedDocument, unique_id=document_id)
        #  i want also to return document type
        json_data = generated_document.json_content
        document_type = generated_document.document_type

        return Response(
            {"document_type": document_type, "json_data": json_data},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Document not found: {e}"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
def get_document_pdf(request, document_id):
    """
    API endpoint to serve the generated document as a PDF.
    """
    try:
        generated_document = get_object_or_404(GeneratedDocument, unique_id=document_id)
        json_data = generated_document.json_content
        document_type = generated_document.document_type

        # mapping document type to template
        template_mapping = {
            "cover_letter": "document_templates/cover_letter.html",
            "recommendation_letter": "document_templates/recommendation_letter.html",
            "motivation_letter": "document_templates/motivation_letter.html",
        }
        template_name = template_mapping.get(document_type, "document-default.html")

        # Convert YAML content to PDF
        pdf_data = generate_pdf_from_resume_data(
            json_data, template_name, chosen_theme="", sections_sort=None, hidden_sections=None
        )

        if pdf_data:

            pdf_buffer = io.BytesIO(pdf_data)
            response = StreamingHttpResponse(
                file_iterator(pdf_buffer), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                'inline; filename="generated_document.pdf"'
            )
            response["Content-Length"] = len(pdf_data)
            return response
        else:
            return Response(
                {"error": "Error generating PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as e:
        return Response(
            {"error": f"Document not found: {e}"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
def get_document_docx(request, document_id):
    """
    API endpoint to serve the generated document as a Word (.docx) file.
    """
    try:
        generated_document = get_object_or_404(GeneratedDocument, unique_id=document_id)
        json_data = generated_document.json_content
        document_type = generated_document.document_type

        # mapping document type to template
        template_mapping = {
            "cover_letter": "document_templates/cover_letter.html",
            "recommendation_letter": "document_templates/recommendation_letter.html",
            "motivation_letter": "document_templates/motivation_letter.html",
        }
        template_name = template_mapping.get(document_type, "document-default.html")

        # Generate DOCX using WeasyPrint PDF conversion
        docx_buffer = generate_docx_from_template(
            json_data, template_name, chosen_theme="", sections_sort=None, hidden_sections=None
        )

        if docx_buffer:
            response = FileResponse(
                docx_buffer,
                as_attachment=True,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{document_type}_{document_id}.docx"'
            )
            return response
        else:
            return Response(
                {"error": "Error generating Word document"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as e:
        return Response(
            {"error": f"Document not found: {e}"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["PUT"])
def update_document(request, document_id):
    """
    API endpoint to update the generated document.
    """
    try:
        generated_document = get_object_or_404(GeneratedDocument, unique_id=document_id)
        json_content = request.data  # the json content from the frontend

        # Update the YAML content in the database
        generated_document.json_content = json_content
        generated_document.save()

        return Response(
            {"message": "Document updated successfully"}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": f"Error updating document: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


##################################### ATS Checker #####################################

from .tasks import generate_and_save_resume_task  # Import the Celery task
import logging  # Import logging

logger = logging.getLogger(__name__)  # Setup logger for the view


@api_view(["POST"])
@require_feature("ats_checker")  # Add this decorator
def ats_checker(request):
    """
    Checks resume against a job description using an ATS service.
    Conditionally triggers background generation of resume data (cache)
    or a full resume save (DB) based on authentication and user preference.
    Returns the ATS checker result and the task ID (if generation was triggered).
    """
    generation_task_id = None  # Initialize task ID as None

    try:
        uploaded_file = request.FILES.get("resume")
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Extract text and form data
        text = extract_text_from_file(uploaded_file)
        form_data = json.loads(request.POST.get("formData", "{}"))
        logger.debug(f"DEBUG: form_data: {form_data}", flush=True)
        job_description = form_data.get("description") or ""
        language = form_data.get("targetLanguage") or "en"
        target_role = form_data.get("targetRole") or ""
        # Get the new flag, default to True if not provided
        generate_new_resume_flag = form_data.get("generate_new_resume", True)

        # --- 1. Call ATS Checker Service (Synchronous) ---
        # ... (Keep existing ATS call logic - ensure ats_result is populated) ...
        input_data_ats = {
            "input": {
                "input_text": text,
                "job_description": job_description,
                "language": language,
                "user_input_role": target_role,
            }
        }
        if job_description:
            ai_service_url_ats = os.environ.get("AI_SERVICE_URL") + "ats_checker/invoke"
        else:
            ai_service_url_ats = (
                os.environ.get("AI_SERVICE_URL") + "ats_checker_no_job_desc/invoke"
            )

        ats_result = None
        try:
            logger.info("Calling ATS checker service...")
            response_ats = requests.post(
                ai_service_url_ats, json=input_data_ats, timeout=60
            )
            response_ats.raise_for_status()
            ats_result = response_ats.json().get("output")
            logger.info("ATS checker service call successful.")
        except requests.exceptions.Timeout:
            logger.error("Error calling ATS checker service: Request timed out")
            return Response(
                {"error": "ATS checker service timed out."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling ATS checker service: {e}")
            error_detail = f"Failed to get ATS score: {e}"
            if e.response is not None:
                error_detail += f" - Status: {e.response.status_code}, Response: {e.response.text[:500]}"
            return Response(
                {"error": error_detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except json.JSONDecodeError:
            logger.error(f"Error decoding ATS checker response: {response_ats.text}")
            return Response(
                {"error": "Invalid response from ATS checker service"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if ats_result is None:
            logger.error("ATS result is None after supposed successful call.")
            return Response(
                {"error": "Failed to retrieve ATS score, cannot proceed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # --- 2. Conditionally Trigger Resume Generation Task ---
        if request.user.is_authenticated:
            logger.info(f"User {request.user.id} is authenticated.")
            if generate_new_resume_flag:
                logger.info(
                    "generate_new_resume flag is True. Triggering 'generate_and_save_resume_task'."
                )
                user_id = request.user.id
                task_result_object = generate_and_save_resume_task.delay(
                    user_id=user_id,
                    input_text=text,
                    job_description=job_description,
                    language=language,
                    ats_result=ats_result,
                )
                generation_task_id = task_result_object.id
                logger.info(
                    f"DB Save Task triggered with ID: {generation_task_id} for user {user_id}"
                )
            else:
                logger.info(
                    "generate_new_resume flag is False. Skipping resume generation task."
                )
                # generation_task_id remains None
        else:
            logger.info(
                "User is not authenticated. Triggering 'generate_resume_data_task' (cache)."
            )
            task_result_object = generate_resume_data_task.delay(
                input_text=text,
                job_description=job_description,
                language=language,
                ats_result=ats_result,
            )
            generation_task_id = task_result_object.id
            logger.info(f"Cache Task triggered with ID: {generation_task_id}")

        # --- 3. Return ATS Checker Response AND Task ID (if any) ---
        logger.info(
            "Returning ATS result and generation task ID (if applicable) to client."
        )
        response_payload = {
            "ats_result": ats_result,
            "generation_task_id": generation_task_id,  # Will be None if generation was skipped
        }
        return Response(response_payload, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        logger.warning("Invalid formData provided in request.")
        return Response(
            {"error": "Invalid formData provided"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(f"Unexpected error in ats_checker view: {e}")
        return Response(
            {"error": "An unexpected server error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


###### Saving Resume After AUTH ########


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])  # Ensure user is logged in
def save_generated_resume(request):
    """
    Retrieves generated resume data from cache using a task_id
    and saves it as a Resume object for the authenticated user.
    """
    task_id = request.data.get("generation_task_id")
    if not task_id:
        return Response(
            {"error": "generation_task_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    cache_key = f"generated_resume_data_{task_id}"

    try:
        # 1. Retrieve data from cache
        generated_data = cache.get(cache_key)

        if generated_data is None:
            logger.warning(
                f"No cached data found for key {cache_key} for user {user.id}. Task might have expired, failed, or ID is wrong."
            )
            # Optionally check AsyncResult status here for more context
            task_status_result = AsyncResult(task_id)
            status_info = task_status_result.status
            if status_info == states.FAILURE:
                return Response(
                    {"error": "Resume generation task failed previously. Cannot save."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "error": "Generated resume data not found or expired. Please generate again."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Check if resume already created from this task (optional but recommended)
        # Add a field to Resume model, e.g., `generation_task_id = models.CharField(max_length=50, null=True, blank=True, unique=True)`
        # if Resume.objects.filter(generation_task_id=task_id).exists():
        #     logger.warning(f"Resume already created from task {task_id} for user {user.id}.")
        #     existing_resume = Resume.objects.get(generation_task_id=task_id)
        #     return Response({"resume_id": existing_resume.id, "message": "Resume already exists."}, status=status.HTTP_200_OK)

        # 3. Extract data (ensure keys match what's stored in cache)
        title = generated_data.get("title", "Generated Resume")
        description = generated_data.get("description", "")
        icon = generated_data.get("fontawesome_icon", "")
        resume_data = generated_data.get("resume")  # Main resume content
        about = generated_data.get(
            "about_candidate", ""
        )  # Or "about" depending on task output
        job_search_keywords = generated_data.get("job_search_keywords", "")
        if not resume_data:
            logger.error(
                f"Cached data for task {task_id} is missing 'resume' content for user {user.id}."
            )
            return Response(
                {"error": "Invalid cached resume data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Save the Resume object
        is_default = not Resume.objects.filter(user=user).exists()

        # resume obj
        resume_obj = {
            "user": user,
            "resume": resume_data,
            "job_search_keywords": job_search_keywords,
            "is_default": is_default,
            "title": title,
            "about": about,
            "icon": icon,
            "description": description,
        }

        new_resume = Resume.objects.create(**resume_obj)
        logger.info(
            f"Successfully saved resume with ID {new_resume.id} for user {user.id} from task {task_id}."
        )

        # 5. Optionally delete the cache entry now that it's saved
        cache.delete(cache_key)
        logger.info(f"Deleted cache entry {cache_key}.")

        # 6. Return the new resume ID
        return Response(
            {
                "resume_id": new_resume.id,
                "resume_data": resume_obj,
                "message": "Resume saved successfully.",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.exception(
            f"Error saving generated resume for user {user.id} from task {task_id}: {e}"
        )
        return Response(
            {"error": "An unexpected error occurred while saving the resume."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


from .serializers import ResumeSerializer, UserProfileSerializer
from .models import UserProfile
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def user_profile(request):
    """
    Get or update user profile including avatar
    """
    user = request.user
    profile = UserProfile.get_or_create_profile(user)
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = UserProfileSerializer(profile, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    """
    Upload and crop avatar image
    """
    try:
        avatar_data = request.data.get('avatar')
        
        if not avatar_data:
            return Response(
                {'error': 'No avatar data provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate base64 image
        if not avatar_data.startswith('data:image/'):
            return Response(
                {'error': 'Invalid image format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save avatar to user profile
        user = request.user
        profile = UserProfile.get_or_create_profile(user)
        profile.avatar = avatar_data
        profile.save()
        
        return Response({
            'message': 'Avatar uploaded successfully',
            'avatar': avatar_data
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to upload avatar: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_avatar(request):
    """
    Remove user avatar
    """
    try:
        user = request.user
        profile = UserProfile.get_or_create_profile(user)
        profile.avatar = None
        profile.save()
        
        return Response({'message': 'Avatar removed successfully'})
        
    except Exception as e:
        return Response(
            {'error': f'Failed to remove avatar: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_avatar(request):
    """
    Get current user's avatar
    """
    user = request.user
    profile = UserProfile.get_or_create_profile(user)
    return Response({
        'avatar': profile.avatar,
        'hasAvatar': bool(profile.avatar)
    })
