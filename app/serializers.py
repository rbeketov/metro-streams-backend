from rest_framework import serializers
from app.models import ApplicationsForModeling
from app.models import ModelingApplications
from app.models import Users
from app.models import TypesOfModeling

class ApplicationsForModelingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationsForModeling
        fields = [
            'application_id',
            'user_id',
            'moderator_id',
            'date_application_create',
            'date_application_accept',
            'date_application_complete',
            'metro_name',
            'status_application',
        ]

class ModelingApplicationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelingApplications
        fields = [
            'modeling_id',
            'application_id',
        ]

class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = [
            'user_id',
            'first_name',
            'second_name',
            'email',
            'login',
            'password',
            'role',
        ]

class TypesOfModelingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypesOfModeling
        fields = [
            'modeling_id',
            'modeling_name',
            'modeling_description',
            'modeling_price',
            'modeling_image_url',
            'modeling_status',
        ]