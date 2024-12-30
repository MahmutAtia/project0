import time
def cleanup_old_sessions(request):
    """Remove session data older than 1 hour"""
    current_time = int(time.time())
    keys_to_delete = []
    
    for key in request.session.keys():
        if key.startswith('temp_resume_'):
            data = request.session.get(key)
            if data and (current_time - data['created_at']) > 3600:
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del request.session[key]



        