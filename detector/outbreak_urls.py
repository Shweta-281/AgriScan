from django.urls import path
from . import views

urlpatterns = [
    path('', views.outbreak_map, name='outbreak_map'),
    path('data/', views.outbreak_data, name='outbreak_data'),
]