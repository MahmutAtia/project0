from rest_framework import generics, permissions, status
from .models import Resume
from .serializers import ResumeSerializer
from django.http import Http404
from .utils import cleanup_old_sessions
from rest_framework.response import Response
from django.contrib.auth.models import User
import requests # For calling the AI service
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.utils import timezone
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
        print(f"DEBUG: Looking up key: {session_key}")
        
        if session_key.startswith('temp_resume_'):
            cached_data = cache.get(session_key)
            print(f"DEBUG: Redis data found: {cached_data}")
            
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
                    print(f"DEBUG: Error parsing cached data: {e}")
                    raise Http404("Invalid cache data")
            
            raise Http404("Temporary resume not found or expired")
        
        if self.request.user.is_authenticated:
            print(f"DEBUG: User is authenticated: {self.request.user}")
            print(Resume.objects.get(id=session_key, user=self.request.user))
            return Resume.objects.get(id=session_key, user=self.request.user)
            
        raise Http404("Resume not found")   


@api_view(["POST"])
def generate_resume(request):
    # Test Redis connection
    try:
        cache.set('test_key', 'test_value')
        test_value = cache.get('test_key')
        print(f"DEBUG: Redis test - {test_value}")
    except Exception as e:
        print(f"DEBUG: Redis connection error - {str(e)}")
        return Response({"error": "Redis connection failed"}, status=500)

    input_data = request.data
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "genereate_from_input/invoke"
    response = requests.post(ai_service_url, json=input_data)
    print(input_data.keys())

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
    input_data = request.data
    print(input_data)
    ai_service_url = os.environ.get("AI_SERVICE_URL") + "genereate_from_job_desc/invoke"
    print(ai_service_url)
    response = requests.post(ai_service_url, json=input_data)

    if response.status_code == 200:
        try:
            generated_resume_yaml = response.json().get("output")
            generated_resume_data = yaml.safe_load(generated_resume_yaml)
            
            ## Extract the data
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
                print(f"DEBUG: Stored in Redis - {stored_data}")
                
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
            return Response(
                {"error": f"Invalid data received from AI service: {e}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        return Response(response.json(), status=response.status_code)
    
                