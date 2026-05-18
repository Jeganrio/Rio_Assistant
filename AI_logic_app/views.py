from django.shortcuts import render
from django.http import JsonResponse
from . import AI_logic  

def start_ai(request):
    try:
        AI_logic.startup()
        return JsonResponse({'status': 'success', 'message': 'CUBY started successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'CUBY STOPPED: {str(e)}'})

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def user_manual(request):
    return render(request, 'user_manual.html')

def troubleshoot(request):
    return render(request, 'troubleshoot.html')

