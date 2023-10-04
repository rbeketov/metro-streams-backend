from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status

from app.serializers import TypesOfModelingSerializer
from app.serializers import ModelingApplicationsSerializer
from app.serializers import ApplicationsForModelingSerializer
from app.serializers import UsersSerializer

from app.models import TypesOfModeling
from app.models import ModelingApplications
from app.models import ApplicationsForModeling
from app.models import Users

from rest_framework.decorators import api_view

from django.db import connection
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q


# Domain Users
    # in process


# Domain ApplicationsForModeling
@api_view(['Post'])
def create_applications(request, format=None):
    try:
        data = request.data

        required_fields = ['user_id', 'metro_name', 'modeling_id']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Field '{field}' is missing in the request data")
        
        # Проверьте существование пользователя
        user = Users.objects.get(pk=data['user_id'])

        application = ApplicationsForModeling(
            user=user,
            metro_name=data['metro_name']
        )
        application.save()

        modeling_ids = data['modeling_id']
        for modeling_id in modeling_ids:
            modeling_application = ModelingApplications(
                modeling_id=modeling_id,
                application=application
            )
            modeling_application.save()

        return Response(application.id, status=status.HTTP_201_CREATED)
    
    except Users.DoesNotExist:
        return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    except KeyError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_application(request, pk, format=None):
    try:
        applications = ApplicationsForModeling.objects.filter(application_id=pk).values(
            'modelingapplications__modeling__modeling_name',
            'modelingapplications__modeling__modeling_description',
            'metro_name',
            'date_application_create',
            'date_application_accept',
            'date_application_complete',
            'status_application',
            'modelingapplications__modeling__modeling_price',
            'modelingapplications__modeling__modeling_image_url',
            'user__first_name',
            'user__second_name',
            'user__email',
            'moderator__first_name',
            'moderator__second_name',
            'moderator__email'
        )

        if applications:
            result = []
            user_data = {
                    'first_name': applications[0]['user__first_name'],
                    'second_name': applications[0]['user__second_name'],
                    'email': applications[0]['user__email']
                }

            moderator_data = {
                'first_name': applications[0]['moderator__first_name'],
                'second_name': applications[0]['moderator__second_name'],
                'email': applications[0]['moderator__email']
            }

            for application in applications:
                data = {
                        'modeling_name': application['modelingapplications__modeling__modeling_name'],
                        'modeling_description': application['modelingapplications__modeling__modeling_description'],
                        'metro_name': application['metro_name'],
                        'date_application_create': application['date_application_create'],
                        'date_application_accept': application['date_application_accept'],
                        'date_application_complete': application['date_application_complete'],
                        'status_application': application['status_application'],
                        'modeling_price': application['modelingapplications__modeling__modeling_price'],
                        'modeling_image_url': application['modelingapplications__modeling__modeling_image_url'],
                    }
                result.append(data)
    
            response_json = {
                'user_data': user_data,
                'moderator_data': moderator_data,
                'modeling' : result
            }
    
            return Response(response_json, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)





# Domain TypeOfModeling
@api_view(['Get'])
def search_modeling(request, format=None): # add check_authorization
    query = request.GET.get('q')
    if query:
        modeling_objects = TypesOfModeling.objects.filter(Q(modeling_name__icontains=query.lower()), modeling_status="WORK")
    else:
        query = ''
        modeling_objects = TypesOfModeling.objects.filter(modeling_status="WORK")

    serializer = TypesOfModelingSerializer(modeling_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['Get'])
def get_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    serializer = TypesOfModelingSerializer(modeling_object)
    return Response(serializer.data)


@api_view(['Delete'])
def del_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'DELE'
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['Put'])
def recover_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'WORK'
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['Put'])
def edit_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    try:
        data = request.data

        modeling_object.modeling_name = data.get('modeling_name', modeling_object.modeling_name)
        modeling_object.modeling_description = data.get('modeling_description', modeling_object.modeling_description)
        modeling_object.modeling_price = data.get('modeling_price', modeling_object.modeling_price)
        modeling_object.modeling_image_url = data.get('modeling_image_url', modeling_object.modeling_image_url)
    
        modeling_object.save()

        modeling_object.refresh_from_db()
        serializer = TypesOfModelingSerializer(modeling_object)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['Post'])
def create_type_modeling(request, format=None):
    try:
        print(request.data)
        data = request.data

        modeling_name = data.get('modeling_name')
        modeling_description = data.get('modeling_description')
        modeling_price = data.get('modeling_price')
        modeling_image_url = data.get('modeling_image_url')

        new_modeling_object = TypesOfModeling(
            modeling_name=modeling_name,
            modeling_description=modeling_description,
            modeling_price=modeling_price,
            modeling_image_url=modeling_image_url
        )

        new_modeling_object.save()

        created_modeling_object = TypesOfModeling.objects.get(pk=new_modeling_object.pk)
        serializer = TypesOfModelingSerializer(created_modeling_object)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)
   
