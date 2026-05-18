from django.shortcuts import render
from django.http import JsonResponse
from AI_logic_app.AI_logic import startup  

def start_ai(request):
    # Call the startup function here
    try:
        startup()
        return JsonResponse({'status': 'success', 'message': 'CUBY started successfully'})
    

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'CUBY STOPPED: {str(e)}'})

    
def home(request, content):
    context = None
    return render(request, 'my_home.html', context)

