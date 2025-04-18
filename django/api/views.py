from rest_framework import generics, permissions, status
from .models import Resume
from .serializers import ResumeSerializer
from django.http import Http404
from .utils import cleanup_old_sessions, extract_text_from_file,generate_pdf_from_resume_data
from rest_framework.response import Response
from django.contrib.auth.models import User
import requests # For calling the AI service
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, FileResponse

from datetime import datetime  # Import datetime class directly
import json
import yaml
import os
import time





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