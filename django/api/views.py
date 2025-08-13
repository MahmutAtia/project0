from rest_framework import generics, permissions, status
from .models import Resume, GeneratedWebsite, GeneratedDocument,BackgroundTask,UserProfile
from .serializers import ResumeSerializer, UserProfileSerializer
from django.http import Http404
from .utils import (
    generate_pdf_from_resume_data,
    generate_html_from_yaml,
    generate_docx_from_template,
    generate_website_slug
)
from rest_framework.response import Response
from django.contrib.auth.models import User
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
    HttpResponseServerError,
)
import uuid
import io




import httpx  # Add httpx for async requests
from asgiref.sync import sync_to_async  # For wrapping sync code if needed

from rest_framework import permissions
from django.core.cache import cache

from plans.decorators import require_feature

import logging  # For logging errors and info
logger = logging.getLogger(__name__)


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

############################# generate website resume #############################

@api_view(["POST"])
def save_generated_website(request):
    """
    Finds a background task and creates a GeneratedWebsite instance from the task's result.
    """
    task_id = request.data.get("generation_task_id")
    if not task_id:
        return Response({"error": "Missing generation_task_id."}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    try:
        # 1. Retrieve the task from the database
        task = BackgroundTask.objects.get(id=task_id)
        # 2. Security and State Check
        if task.user and task.user != user:
            return Response({"error": "You do not have permission to access this task."}, status=status.HTTP_403_FORBIDDEN)

        # TODO: Check if the task has already been processed
        # Prevent re-processing a task that already created a website
        # if GeneratedWebsite.objects.filter(unique_id=task_id).exists():  # using task_id as unique_id to avoid conflicts
        #     # If a website already generated for this task, return early
        #     logger.info(f"Website already generated for task {task_id}.")
        #     return Response({"message": "Website already generated for this task.", "website_uuid": task_id}, status=status.HTTP_200_OK)

        # 3. Create the GeneratedWebsite instance
        resume = get_object_or_404(Resume, pk=task.result.get("resume_id"), user=user)

        # check if there is a resume with that id has already a website
        if GeneratedWebsite.objects.filter(resume=resume).exists():
            return Response({"message": "Website already exists for this resume.", "website_uuid": resume.personal_website.unique_id}, status=status.HTTP_200_OK)

        generated_website = GeneratedWebsite.objects.create(
            resume=resume,
            unique_id= generate_website_slug(resume.user, resume.id),
            json_content=task.result.get("website", {}),
        )
        return Response({"message": "Website generated successfully.", "website_uuid": generated_website.unique_id}, status=status.HTTP_201_CREATED)

    except BackgroundTask.DoesNotExist:
        return Response({"error": "Background task not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"Error saving generated website: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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


###### Saving Resume After AUTH ########


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def save_generated_resume(request):
    """
    Finds a background task, claims it for the now-authenticated user,
    and creates a Resume instance from the task's result.
    This replaces the old cache-based retrieval.
    """
    task_id = request.data.get("generation_task_id")
    if not task_id:
        return Response(
            {"error": "generation_task_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user

    try:
        # 1. Retrieve the task from the database
        task = BackgroundTask.objects.get(id=task_id)

        # 2. Security and State Check
        if task.user and task.user != user:
            logger.warning(f"User {user.id} attempted to claim task {task_id} belonging to user {task.user.id}.")
            return Response({"error": "This task does not belong to you."}, status=status.HTTP_403_FORBIDDEN)

        # Prevent re-processing a task that already created a resume
        if Resume.objects.filter(generation_task_id=task_id).exists():
            existing_resume = Resume.objects.get(generation_task_id=task_id)
            logger.warning(f"Resume {existing_resume.id} already created from task {task_id}.")
            serializer = ResumeSerializer(existing_resume)
            return Response({
                "resume_id": existing_resume.id,
                "resume_data": serializer.data,
                "message": "Resume already created from this task."
            }, status=status.HTTP_200_OK)

        # 3. Handle task based on its status
        if task.status == 'SUCCESS':
            generated_data = task.result
            if not generated_data or "resume" not in generated_data:
                logger.error(f"Task {task_id} succeeded but has invalid result data.")
                task.status = 'FAILURE'
                task.error_message = "Task completed with invalid or missing result data."
                task.save()
                return Response({"error": "Task completed with invalid data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Extract data and create the Resume
            title = generated_data.get("title", "Generated Resume")
            description = generated_data.get("description", "")
            icon = generated_data.get("fontawesome_icon", "")
            resume_data = generated_data.get("resume")
            about = generated_data.get("about_candidate", "")
            job_search_keywords = generated_data.get("job_search_keywords", "")

            is_default = not Resume.objects.filter(user=user).exists()

            new_resume = Resume.objects.create(
                user=user,
                resume=resume_data,
                job_search_keywords=job_search_keywords,
                is_default=is_default,
                title=title,
                about=about,
                icon=icon,
                description=description,
                generation_task_id=task_id  # Link the resume to the task
            )
            
            # Claim the task by assigning the user
            if not task.user:
                task.user = user
                task.save()

            logger.info(f"Successfully saved resume {new_resume.id} for user {user.id} from task {task_id}.")
            
            serializer = ResumeSerializer(new_resume)
            return Response({
                "resume_id": new_resume.id,
                "resume_data": serializer.data,
                "message": "Resume saved successfully."
            }, status=status.HTTP_201_CREATED)

        elif task.status == 'PENDING':
            return Response({"error": "Resume generation is still in progress. Please wait."}, status=status.HTTP_202_ACCEPTED)
        
        elif task.status == 'FAILURE':
            return Response({"error": f"Resume generation failed: {task.error_message}"}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"error": f"Unknown task status: {task.status}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except BackgroundTask.DoesNotExist:
        logger.warning(f"User {user.id} requested non-existent task ID {task_id}.")
        return Response({"error": "Generated resume data not found. The task may have expired or the ID is incorrect."}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.exception(f"Error saving generated resume for user {user.id} from task {task_id}: {e}")
        return Response({"error": "An unexpected error occurred while saving the resume."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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




######################### Task Management API Endpoints #########################


# --- PUBLIC ENDPOINT FOR FRONTEND ---
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_task_status(request, task_id):
    """Lets the frontend check the status of a task."""
    try:
        task = BackgroundTask.objects.get(id=task_id)
        return Response({
            "task_id": task.id,
            "status": task.status,
            "result": task.result,
            "error": task.error_message
        })
    except BackgroundTask.DoesNotExist:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

# --- INTERNAL ENDPOINTS FOR FASTAPI ---
# You should secure these with an API key or internal network restrictions in production

@api_view(["POST"])
@permission_classes([permissions.AllowAny]) # Internal access only
def internal_create_task(request):
    """Creates a task record and returns its ID."""
    user_id = request.data.get("user_id")
    user = None
    
    if user_id:
        try:
            # Find the user if an ID is provided
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Log this, but don't fail the request. The task will be anonymous.
            logger.warning(f"internal_create_task called with non-existent user_id: {user_id}")
    
    try:
        # Create the task with the user object (which can be None)
        task = BackgroundTask.objects.create(user=user, status='PENDING')
        logger.info(f"Internal task {task.id} created for user: {user_id if user_id else 'Anonymous'}")
        return Response({"task_id": str(task.id)}, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.exception(f"Failed to create internal task: {e}")
        return Response({"error": "Failed to create task record."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([permissions.AllowAny]) # Internal access only
def internal_update_task(request):
    """Updates a task with a result or an error."""
    task_id = request.data.get("task_id")
    status = request.data.get("status")
    result = request.data.get("result")
    error = request.data.get("error")
    
    try:
        task = BackgroundTask.objects.get(id=task_id)
        task.status = status
        task.result = result
        task.error_message = error
        task.save()
        return Response({"message": "Task updated"})
    except BackgroundTask.DoesNotExist:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)