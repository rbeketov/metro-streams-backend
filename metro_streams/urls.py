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
from django.urls import include, path, re_path
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()


schema_view = get_schema_view(
    openapi.Info(
        title="MetroStreams API",
        default_version='v1',
        description="MetroStreams",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
    
    path(r'modelings/', views.search_modeling, name='search_modeling'),
    path(r'modelings/<int:pk>/', views.get_type_modeling, name='modeling_detail'),
    path(r'modelings/<int:pk>/delete/', views.del_type_modeling, name='delete_type_modeling'),
    path(r'modelings/<int:pk>/recover/', views.recover_type_modeling, name='recover_type_modeling'),
    path(r'modelings/<int:pk>/edit/', views.edit_type_modeling , name='edit_type_modeling'),
    path(r'modelings/create/', views.create_type_modeling , name='create_type_modeling'),

    path(r'applications/', views.search_applications, name='search_applications'),
    path(r'applications/<int:pk>/', views.get_application, name='get_application_on_id'),
    path(r'applications/create/', views.add_modeling_to_applications, name='add_modeling_to_applications'),
    path(r'applications/<int:pk>/take/', views.take_application, name='take_application'),
    path(r'applications/<int:pk>/edit/', views.edit_application, name='edit_application'),
    path(r'applications/<int:pk>/delete_modeling/', views.del_modeling_from_application, name='del_modeling_from_application'),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
