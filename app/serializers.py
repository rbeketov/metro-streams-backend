from rest_framework import serializers
from app.models import ApplicationsForModeling
from app.models import ModelingApplications
from app.models import Users
from app.models import TypesOfModeling


class ApplicationsForModelingSerializer(serializers.ModelSerializer):
    user_first_name = serializers.CharField(source='user.first_name')
    user_second_name = serializers.CharField(source='user.second_name')
    moderator_first_name = serializers.CharField(source='moderator.first_name', required=False)
    moderator_second_name = serializers.CharField(source='moderator.second_name', required=False)

    class Meta:
        model = ApplicationsForModeling
        fields = '__all__'


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
            'modeling_image_url'
        ]