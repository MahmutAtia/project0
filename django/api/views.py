from rest_framework import generics, permissions, status
from .models import Resume, GeneratedWebsite,GeneratedDocument
from .serializers import ResumeSerializer
from django.http import Http404
from .utils import cleanup_old_sessions, extract_text_from_file,generate_pdf_from_resume_data,generate_html_from_yaml
from rest_framework.response import Response
from django.contrib.auth.models import User
import requests # For calling the AI service
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, FileResponse, HttpResponse, JsonResponse
import textwrap
from datetime import datetime  # Import datetime class directly
import json
import yaml
import os
import time
import uuid

FRONTEND_BASE_URL="http://localhost:8000" # settings.FRONTEND_BASE_URL


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)
    
    

class ResumeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResumeSerializer
    permission_classes = []
    lookup_field = 'pk'
    
    def get_object(self):
        session_key = str(self.kwargs.get('pk'))
        
        if session_key.startswith('temp_resume_'):
            cached_data = cache.get(session_key)
            
            if cached_data:
                try:
                    resume_data = json.loads(cached_data)
                    class TempResume:
                        def __init__(self, data):
                            self.name = f"Temporary Resume {session_key}"
                            self.data = data['data']
                            # Fix timestamp conversion
                            timestamp = float(data['created_at'])
                            dt = datetime.fromtimestamp(timestamp)
                            self.created_at = timezone.make_aware(dt)
                            self.updated_at = self.created_at
                    
                    return TempResume(resume_data)
                except (json.JSONDecodeError, KeyError) as e:
                    raise Http404("Invalid cache data")
            
            raise Http404("Temporary resume not found or expired")
        
        if self.request.user.is_authenticated:
            return Resume.objects.get(id=session_key, user=self.request.user)
            
        raise Http404("Resume not found")   


@api_view(["POST"])
def generate_resume(request):
    # Test Redis connection
    try:
        cache.set('test_key', 'test_value')
        test_value = cache.get('test_key')
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
            title = generated_resume_data.get("title") # the title of the resume
            description = generated_resume_data.get("description") # the description of the resume
            icon = generated_resume_data.get("primeicon") # the icon of the resume
            other_docs = generated_resume_data.get("other_docs") # a list of other documents
            resume_data = generated_resume_data.get("resume") # the resume data
            about = generated_resume_data.get("about") # the about of the resume
            
            
            if not request.user.is_authenticated:
                timestamp = int(time.time())
                session_key = f"temp_resume_{timestamp}"
                
                # Store directly in Redis cache
                cache_data = {
                    'data': resume_data,
                    'created_at': timestamp,
                }
                
                cache.set(session_key, json.dumps(cache_data), timeout=3600)
                
                # Verify storage
                stored_data = cache.get(session_key)
                # print(f"DEBUG: Stored in Redis - {stored_data}")
                
                response = Response({
                    'id': session_key,
                    'message': 'Resume stored in Redis',
                }, status=status.HTTP_201_CREATED)
                
                return response
            
            else: # the user is authenticated it will save the resume in the database
                
                
                # if this the first resume of the user it will set it as the default resume
                if not Resume.objects.filter(user=request.user).exists():
                    is_default = True
                else:
                    is_default = False
                    
                resume = Resume.objects.create(user=request.user, resume=resume_data, other_docs=other_docs, is_default=is_default, title=title, about=about ,icon=icon, description=description)
                print(f"DEBUG: Resume saved - {resume}")
                return Response({
                    'id': resume.id,
                    'message': 'Resume saved successfully',
                }, status=status.HTTP_201_CREATED)
                                
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            print(generated_resume_yaml)
            return Response(
                {"error": f"Invalid data received from AI service: {e}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        return Response(response.json(), status=response.status_code)


@api_view(["POST"])
def generate_resume_section(request):
    input_data = request.data
    prompt, section_data = input_data.get("prompt"), input_data.get("sectionData")
    section_yaml = yaml.dump(section_data) # Convert to YAML

    # Call the AI service
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "edit_section/invoke"

    body = {
        "input": {
            "prompt": prompt,
            "section_yaml": section_yaml,
            "section_title": input_data.get("sectionTitle"),
        }
    }
    response = requests.post(ai_service_url, json=body)

    if response.status_code == 200:
        try:
            generated_section_yaml = response.json().get("output")
            generated_section_data = yaml.safe_load(generated_section_yaml)
            print
            return Response(generated_section_data)

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return Response({"error": f"Invalid data received from AI service: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(response.json(), status=response.status_code)



@api_view(["POST"])
def generate_from_job_desc(request):
    try:
        print("DEBUG: Request Headers:", request.headers)
        print("DEBUG: Request Files:", request.FILES)
        print("DEBUG: Request POST Data:", request.POST)

        uploaded_file = request.FILES.get('resume')
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=400)

        print("DEBUG: Uploaded File Name:", uploaded_file.name)
        print("DEBUG: Uploaded File Content Type:", uploaded_file.content_type)
        print("DEBUG: Uploaded File Size:", uploaded_file.size)

        text = extract_text_from_file(uploaded_file)
        print("DEBUG: Extracted Text:", text)

        form_data = json.loads(request.POST.get('formData', '{}'))
        print("DEBUG: Form Data:", form_data)

 

        input_data = {"input" : {
            'input_text': text,
            'job_description': form_data.get('description') or '',
            'language': form_data.get('targetLanguage') or 'en',
            'docs_instructions': "\n".join(
                f"Write a {key} tailored to the job description"
                for key, value in form_data.get('documentPreferences', {}).items()
                if value
            )
        }}

        ai_service_url = os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"

        response = requests.post(ai_service_url, json=input_data)
    
        if response.status_code == 200:
            try:
                generated_resume_yaml = response.json().get("output")
                generated_resume_data = yaml.safe_load(generated_resume_yaml)

                title = generated_resume_data.get("title")
                description = generated_resume_data.get("description")
                icon = generated_resume_data.get("primeicon")
                other_docs = generated_resume_data.get("other_docs")
                resume_data = generated_resume_data.get("resume")
                about = generated_resume_data.get("about")

                if not request.user.is_authenticated:
                    timestamp = int(time.time())
                    session_key = f"temp_resume_{timestamp}"
                    cache_data = {
                        'data': resume_data,
                        'created_at': timestamp,
                    }
                    cache.set(session_key, json.dumps(cache_data), timeout=3600)
                    return Response({
                        'id': session_key,
                        'message': 'Resume stored in Redis',
                    }, status=status.HTTP_201_CREATED)
                else:
                    is_default = not Resume.objects.filter(user=request.user).exists()
                    resume = Resume.objects.create(
                        user=request.user,
                        resume=resume_data,
                        other_docs=other_docs,
                        is_default=is_default,
                        title=title,
                        about=about,
                        icon=icon,
                        description=description
                    )
                    return Response({
                        'id': resume.id,
                        'message': 'Resume saved successfully',
                    }, status=status.HTTP_201_CREATED)
            except (json.JSONDecodeError, yaml.YAMLError) as e:
                return Response(
                    {"error": f"Invalid data received from AI service: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(response.json(), status=response.status_code)
    except Exception as e:
        return Response({'error': str(e)}, status=500)    


################################## genereate_pdf ################################

def file_iterator(file_like, chunk_size=8192):  # 8KB chunk size
    """Generator to stream file in chunks."""
    while True:
        chunk = file_like.read(chunk_size)
        if not chunk:
            break
        yield chunk


    

@api_view(["POST"])
def generate_pdf(request):
    """
    API endpoint to generate and serve a PDF resume.
    """
    resume_id = request.data.get('resumeId')
    template_theme = request.data.get('templateTheme', 'default.html')  # Default value
    chosen_theme = request.data.get('chosenTheme', 'theme-default')

    if not resume_id:
        return Response({"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        resume_data = resume.resume
       

    except Exception as e:
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    pdf_data = generate_pdf_from_resume_data(resume_data, template_theme, chosen_theme)

    if pdf_data:
        # logger.info("PDF data generated successfully.  Type: %s, Length: %s", type(pdf_data), len(pdf_data))
        try:
            # Use the file_iterator with BytesIO
            import io
            pdf_buffer = io.BytesIO(pdf_data)
            response = StreamingHttpResponse(file_iterator(pdf_buffer), # file chuncking is very important, i tried too much to send the whole file at once and it was not working.
                                            content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="generated_resume.pdf"'
            #  Set content length (optional, but good practice)
            response['Content-Length'] = len(pdf_data)
            return response
        except Exception as e:
            # logger.exception("Error creating StreamingHttpResponse:")  # Log this too!
            return Response(
                {"error": f"Error creating response: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        return Response(
            {"error": "Error generating PDF"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
   
     )
        
        
############################# generate website resume #############################

@api_view(["POST"])
def generate_personal_website(request):
    """
    API endpoint to generate and save a personal website.
    """
    resume_id = request.data.get('resumeId')
    preferences = request.data.get('preferences', {})
    
    if not resume_id:
        return Response({"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        resume_data = resume.resume

        # Check if a website has already been generated for this resume
        generated_website = GeneratedWebsite.objects.filter(resume=resume).first()
        if generated_website:
            # Website already exists, return the unique link
            
            return Response({"website_uuid": generated_website.unique_id}, status=status.HTTP_200_OK)

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
        GeneratedWebsite.objects.create(resume=resume, unique_id=unique_id, html_content=full_html)

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
def generate_personal_website_bloks(request):
    """
    API endpoint to generate and save a personal website using Bloks.
    """
    resume_id = request.data.get('resumeId')
    preferences = request.data.get('preferences', {})
    
    if not resume_id:
        return Response({"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        resume_data = resume.resume

        # Check if a website has already been generated for this resume
        generated_website = GeneratedWebsite.objects.filter(resume=resume).first()
        if generated_website:
            # Website already exists, return the unique link
            return Response({"website_uuid": generated_website.unique_id}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Generate the personal website using Bloks
    resume_yaml = yaml.dump(resume_data)
    preferences = yaml.dump(preferences)
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "create_resume_website_bloks/invoke"
    body = {"input": {"resume_yaml": resume_yaml, "preferences": preferences}}

    try:
        ai_response = requests.post(ai_service_url, json=body)
        ai_response.raise_for_status()
        generated_website_bloks_yaml = ai_response.json().get("output")

        # Save the generated website YAML
        unique_id = str(uuid.uuid4())
        GeneratedWebsite.objects.create(
            resume=resume,
            unique_id=unique_id,
            yaml_content=generated_website_bloks_yaml,
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

        yaml_content = generated_website.yaml_content

        # Parse the YAML content
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            # Handle YAML parsing errors
            return Response(
                {"error": f"Error parsing YAML content: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Return the parsed YAML (Python dict/list) as JSON
        return Response(parsed_yaml, status=status.HTTP_200_OK)

    except Exception as e:
        # Catch any other unexpected errors (e.g., database issues)
        print(f"An unexpected error occurred: {e}") # Log the error
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
        json_data = yaml.safe_load(generated_website.yaml_content)
        # Generate the HTML from the YAML data
        full_html = generate_html_from_yaml(json_data)
        return HttpResponse(full_html, content_type="text/html")
    except Exception as e:
        return Response({"error": f"Website not found: {e}"}, status=status.HTTP_404_NOT_FOUND)

        


@api_view(["GET"])
def serve_personal_website(request, unique_id):
    """
    API endpoint to serve a pre-generated personal website.
    """
    try:
        generated_website = get_object_or_404(GeneratedWebsite, unique_id=unique_id)
        return HttpResponse(generated_website.html_content, content_type="text/html")
    except Exception as e:
        return Response({"error": f"Website not found: {e}"}, status=status.HTTP_404_NOT_FOUND)
    
############################## Update yaml website content ##############################
@api_view(["PUT"])
def update_website_yaml(request, unique_id):
    """
    API endpoint to update the YAML content of a personal website.
    """
    try:
        generated_website = get_object_or_404(GeneratedWebsite, unique_id=unique_id)
   
        json_content = request.data #the json content from the frontend has global and code_bloks
        

       
        # Update the YAML content in the database
        generated_website.yaml_content = yaml.dump(json_content)
        generated_website.save()

        return Response({"message": "YAML content updated successfully"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Error updating website: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
############################### edit website block ###############################

@api_view(["POST"])
def edit_website_block(request):
    data = json.loads(request.body)
    resume_id = data.get('resumeId')
    current_name = data.get('blockName')
    current_html = data.get('currentHtml')
    current_css = data.get('currentCss')
    current_js = data.get('currentJs')
    prompt = data.get('prompt')
    artifacts = data.get('artifacts', [])
    
    if not all([resume_id, current_name, prompt]):
            return JsonResponse({'error': 'Missing required parameters.'}, status=400)
        
    # Call the AI service
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "edit_block/invoke"
    body = {
        "input": {
            "current_name": current_name,
            "current_html": textwrap.indent(current_html, '  '),# used to indent the html code
            "current_css":  textwrap.indent(current_css, '  '),# used to indent the css code
            "current_js": textwrap.indent(current_js, '  '),# used to indent the js code
            "prompt": prompt,
            "artifacts": artifacts
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

            return JsonResponse({
                'html': html_code,
                'css': css_code,
                'js': js_code
            }, status=200)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return JsonResponse({"error": f"Invalid data received from AI service: {e}"}, status=500)
    else:
        return JsonResponse({"error": "Error from AI service"}, status=response.status_code)

############################# Documents ##############################

@api_view(["POST"])
def generate_document_bloks(request):
    """
    API endpoint to generate a document using Bloks.
    """
    resume_id = request.data.get('resumeId')
    preferences = request.data.get('preferences', {})
    document_type = request.data.get('documentType', '') 
    language = request.data.get('language', 'en')  # Default to English if not provided
    document_name = request.data.get('documentName', 'Generated Document')  # Default name if not provided
    
    if not resume_id:
        return Response({"error": "resumeId is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        resume = get_object_or_404(Resume, pk=resume_id)
        about = resume.about

        # Check if a document has already been generated for this resume
        generated_document = GeneratedDocument.objects.filter(resume=resume).first()
        if generated_document:
            # Document already exists, return the unique link
            return Response({"document_uuid": generated_document.unique_id}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error fetching resume data: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "create_document/invoke"
    body = {
        "input": {
            "preferences": preferences,
            "document_type": document_type,
            "language": language,
            "about": about,
            "document_name": document_name,
        }
    }
    try:
        ai_response = requests.post(ai_service_url, json=body)
        ai_response.raise_for_status()
        generated_document_json = ai_response.json().get("output")

        # Save the generated document
        unique_id = str(uuid.uuid4())
        GeneratedDocument.objects.create(
            resume=resume,
            unique_id=unique_id,
            json_content=generated_document_json,
        )

        # Return the unique id
        return Response({"document_uuid": unique_id}, status=status.HTTP_201_CREATED)
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
def get_document_pdf(request, document_id):
    """
    API endpoint to serve the generated document as a PDF.
    """
    try:
        generated_document = get_object_or_404(GeneratedDocument, unique_id=document_id)
        json_data = generated_document.json_content

        # Convert YAML content to PDF
        pdf_data = generate_pdf_from_resume_data(json_data, template_theme='document-default.html', chosen_theme='')

        if pdf_data:
            import io
            pdf_buffer = io.BytesIO(pdf_data)
            response = StreamingHttpResponse(file_iterator(pdf_buffer), content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="generated_document.pdf"'
            response['Content-Length'] = len(pdf_data)
            return response
        else:
            return Response({"error": "Error generating PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({"error": f"Document not found: {e}"}, status=status.HTTP_404_NOT_FOUND)

                


# @api_view(["POST"])
# def generate_from_job_desc(request):
#     try:
#         # Handle file upload
#         uploaded_file = request.FILES.get('resume')
#         form_data = json.loads(request.POST.get('formData', '{}'))
        
#         # Extract text based on file type
#         text = ''
#         if uploaded_file.content_type == 'application/pdf':
#             pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
#             text = '\n'.join([page.extract_text() for page in pdf_reader.pages])
            
#         elif uploaded_file.content_type in [
#             'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
#             'application/msword'
#         ]:
#             doc = Document(io.BytesIO(uploaded_file.read()))
#             text = '\n'.join([para.text for para in doc.paragraphs])
            
#         elif uploaded_file.content_type == 'text/plain':
#             text = uploaded_file.read().decode('utf-8')
            
#         else:
#             return Response({'error': 'Unsupported file type'}, status=400)

#         # Prepare input for AI service
#         input_data = {
#             'input_text': text,
#             'job_description': form_data.get('description'),
#             'language': form_data.get('targetLanguage'),
#             'docs_instructions': "\n".join(
#                 f"Write a {key} tailored to the job description" 
#                 for key, value in form_data.get('documentPreferences', {}).items() 
#                 if value
#             )
#         }

#         # Rest of your existing AI service call
#         ai_service_url = f"{os.environ.get('AI_SERVICE_URL')}genereate_from_job_desc/invoke"
#         response = requests.post(ai_service_url, json=input_data)
#         # ... rest of your existing processing logic
        
        

#     except Exception as e:
#         return Response({'error': str(e)}, status=500)