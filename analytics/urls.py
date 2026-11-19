from django.urls import path
from . import views

urlpatterns = [
    path('', views.weather_dashboard, name='weather_dashboard'),
    path('admin-reports/', views.admin_reports, name='admin_reports'),
    path('admin-reports/export/<str:data_type>/<str:file_format>/', views.export_admin_data, name='export_admin_data'),
]