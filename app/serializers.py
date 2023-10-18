from rest_framework import serializers
from app.models import ApplicationsForModeling
from app.models import ModelingApplications
from app.models import Users
from app.models import TypesOfModeling

from app.s3 import get_image_from_s3
from django.utils.encoding import smart_bytes
import base64


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
    modeling_image = serializers.SerializerMethodField()

    class Meta:
        model = TypesOfModeling
        fields = [
            'modeling_id',
            'modeling_name',
            'modeling_description',
            'modeling_price',
            'modeling_image',
        ]

    def get_modeling_image(self, obj):
        request = self.context.get('request')
        image_data = get_image_from_s3(request, obj.modeling_image_url)
        #if image_data:
        #    base64_image = base64.b64encode(image_data).decode('utf-8')
        #    return base64_image
        #return None
        return "hello"#image_data


class ApplicationsForModelingSerializer(serializers.ModelSerializer):
    user_first_name = serializers.CharField(source='user.first_name')
    user_second_name = serializers.CharField(source='user.second_name')
    moderator_first_name = serializers.CharField(source='moderator.first_name', required=False)
    moderator_second_name = serializers.CharField(source='moderator.second_name', required=False)
    
    date_application_create = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    date_application_accept = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    date_application_complete = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

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
