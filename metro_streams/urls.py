"""
URL configuration for metro_streams project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from app import views
from django.urls import include, path
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    
    path(r'modeling/', views.search_modeling, name='search_modeling'),
    path(r'modeling/<int:pk>/', views.get_type_modeling, name='modeling_detail'),
    path(r'modeling/<int:pk>/delete/', views.del_type_modeling, name='delete_type_modeling'),
    path(r'modeling/<int:pk>/recover/', views.recover_type_modeling, name='recover_type_modeling'),
    path(r'modeling/<int:pk>/edit/', views.edit_type_modeling , name='edit_type_modeling'),
    path(r'modeling/create/', views.create_type_modeling , name='create_type_modeling'),

    path(r'application/<int:pk>/', views.get_application, name='get_application_on_id'),
    path(r'application/create/', views.create_applications, name='create_application'),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('admin/', admin.site.urls),
]
