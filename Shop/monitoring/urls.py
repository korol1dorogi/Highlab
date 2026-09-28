from django.urls import path

from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    path('api/report/', views.api_report, name='api_report'),
]
