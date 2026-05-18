from django.urls import path
from . import views

urlpatterns = [
    path("",views.home),
    path('start_ai/', views.start_ai, name='start_ai'),
    path('about/', views.about),
    path('user_manual/', views.user_manual),
    path('troubleshoot/', views.troubleshoot),
]