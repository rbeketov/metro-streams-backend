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

from django.http import HttpRequest
from django.utils import timezone
from django.db import connection
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce

import datetime

# Domain Users
    # in process

# Domain ApplicationsForModeling
@api_view(['GET'])
def search_applications(request, format=None): # add search param))
    query = request.GET.get('name')
    user = request.GET.get('user')
    moderator = request.GET.get('moderator')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    if date_start and date_end:
        date_start = datetime.strptime(date_start, "%Y-%m-%d")
        date_end = datetime.strptime(date_end, "%Y-%m-%d")

    if query and user and moderator:
        applications = ApplicationsForModeling.objects.filter(
            Q(metro_name__icontains=query.lower()) &
            Q(user_id=user) &
            Q(moderator_id=moderator)
        )
    elif query and user:
        applications = ApplicationsForModeling.objects.filter(
            Q(metro_name__icontains=query.lower()) &
            Q(user_id=user)
        )
    elif query and moderator:
        applications = ApplicationsForModeling.objects.filter(
            Q(metro_name__icontains=query.lower()) &
            Q(moderator_id=moderator)
        )
    elif user and moderator:
        applications = ApplicationsForModeling.objects.filter(
            Q(user_id=user) &
            Q(moderator_id=moderator)
        )
    elif user:
        applications = ApplicationsForModeling.objects.filter(
            Q(user_id=user)
        )
    elif moderator:
        applications = ApplicationsForModeling.objects.filter(
            Q(moderator_id=moderator)
        )
    elif query:
        applications = ApplicationsForModeling.objects.filter(
            Q(metro_name__icontains=query.lower())
        )
    else:
        applications = ApplicationsForModeling.objects.all()


    if date_start and date_end:
        applications = applications.filter(
            Q(date_application_create__gte=date_start) &
            Q(date_application_create__lte=date_end)
        )
    elif date_start:
        applications = applications.filter(
            Q(date_application_create__gte=date_start)
        )
    elif date_end:
        applications = applications.filter(
            Q(date_application_create__gte=date_end)
        )

    applications = applications.annotate(
        user_first_name=F('user__first_name'),
        user_second_name=F('user__second_name'),
        moderator_first_name=F('moderator__first_name'),
        moderator_second_name=F('moderator__second_name'),
    )
 
    serializer = ApplicationsForModelingSerializer(applications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def add_modeling_to_applications(request, format=None):
    try:
        data = request.data

        required_fields = ['application_id','user_id', 'metro_name', 'modeling_id']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Field '{field}' is missing in the request data")

        if not isinstance(data['modeling_id'], list):
            raise TypeError("Field \'modeling_id\' must be list")

        user_id = data['user_id']
        modeling_ids = data['modeling_id']
        if data['application_id']:
            application_id = data['application_id']
            application = ApplicationsForModeling.objects.filter(
                application_id=application_id,
                user_id=user_id,
                metro_name=data['metro_name'],
            ).first()

        if not data['application_id'] or not application:
            user = Users.objects.get(pk=user_id)
            application = ApplicationsForModeling.objects.create(
                user=user,
                metro_name=data['metro_name'],
                date_application_create=timezone.now(),
                status_application='INTR',
            )

        conflict_models = []
        for modeling_id in modeling_ids:
            modeling_application = ModelingApplications.objects.filter(
                modeling_id=modeling_id,
                application=application
            ).first()

            if modeling_application:
                conflict_models.append(modeling_id)
        
        if conflict_models:
            return Response(
                {"error": f"Models with IDs {', '.join(map(str, conflict_models))} already exist in this application"},
                status=status.HTTP_409_CONFLICT
            )

        for modeling_id in modeling_ids:
            modeling_application = ModelingApplications.objects.create(
                modeling_id=modeling_id,
                application=application
            )

        request_for_search = HttpRequest()
        request_for_search.method = 'GET'
        search_result = search_applications(request_for_search, format)
        return Response(search_result.data, status=status.HTTP_201_CREATED)

    except Users.DoesNotExist:
        return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_application(request, pk, format=None):
    try:
        applications = ApplicationsForModeling.objects.filter(application_id=pk).values(
            'modelingapplications__modeling__modeling_id',
            'modelingapplications__modeling__modeling_name',
            'modelingapplications__modeling__modeling_description',
            'metro_name',
            'date_application_create',
            'date_application_accept',
            'date_application_complete',
            'status_application',
            'modelingapplications__modeling__modeling_price',
            'modelingapplications__modeling__modeling_image_url',
            'user__user_id',
            'user__first_name',
            'user__second_name',
            'user__email',
            'moderator__user_id',
            'moderator__first_name',
            'moderator__second_name',
            'moderator__email'
        )

        if applications:
            result = []
            user_data = {
                    'user_id': applications[0]['user__user_id'],
                    'first_name': applications[0]['user__first_name'],
                    'second_name': applications[0]['user__second_name'],
                    'email': applications[0]['user__email']
                }

            moderator_data = {
                'moderator_id': applications[0]['moderator__user_id'],
                'first_name': applications[0]['moderator__first_name'],
                'second_name': applications[0]['moderator__second_name'],
                'email': applications[0]['moderator__email']
            }

            for application in applications:
                data = {
                        'modeling_id': application['modelingapplications__modeling__modeling_id'],
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
                'application_id': pk,
                'user_data': user_data,
                'moderator_data': moderator_data,
                'modeling' : result
            }
    
            return Response(response_json, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
def take_application(request, pk, format=None):
    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'moderator_id' in data:
            moderator_id = data['moderator_id']
            moderator = Users.objects.get(pk=moderator_id)

            application.moderator = moderator
            application.save()

            request_for_get_application = HttpRequest()
            request_for_get_application.method = 'GET'
            response = get_application(request_for_get_application, pk)
            return Response(response.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Moderator ID is missing in the request data"}, status=status.HTTP_400_BAD_REQUEST)

    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except Users.DoesNotExist:
        return Response({"error": "Moderator does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
def edit_application(request, pk, format=None):
    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            stat = data['status']
        else:
            return Response({"error": "Status is missing in the request data"}, status=status.HTTP_400_BAD_REQUEST)

        if application.status_application != stat:
            application.status_application = stat
            application.save()
            request_for_get_application = HttpRequest()
            request_for_get_application.method = 'GET'
            response = get_application(request_for_get_application, pk)
            return Response(response.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": f"Application {pk} is already {stat}"}, status=status.HTTP_400_BAD_REQUEST)

    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def del_modeling_from_application(request, pk, format=None):
    try:
        application = ApplicationsForModeling.objects.get(pk=pk)
        modeling_id = request.data.get('modeling_id')

        modeling_application = ModelingApplications.objects.filter(
            application=application, modeling_id=modeling_id).first()

        if modeling_application:
            modeling_application.delete()
            request_for_get_application = HttpRequest()
            request_for_get_application.method = 'GET'
            response = get_application(request_for_get_application, pk)
            return Response(response.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Modeling not found in the application"}, status=status.HTTP_404_NOT_FOUND)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Application does not exist"}, status=status.HTTP_404_NOT_FOUND)


# Domain TypeOfModeling
@api_view(['GET'])
def search_modeling(request, format=None): # add check_authorization
    query_name = request.GET.get('name')
    sort_by_price = request.GET.get('price')

    if query_name:
        modeling_objects = TypesOfModeling.objects.filter(Q(modeling_name__icontains=query_name.lower()))
    else:
        modeling_objects = TypesOfModeling.objects.filter(modeling_status="WORK")

    if sort_by_price == 'asc':
        modeling_objects = modeling_objects.order_by('modeling_price')
    elif sort_by_price == 'desc':
        modeling_objects = modeling_objects.order_by('-modeling_price')

    serializer = TypesOfModelingSerializer(modeling_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['GET'])
def get_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    serializer = TypesOfModelingSerializer(modeling_object)
    return Response(serializer.data)


@api_view(['DELETE'])
def del_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'DELE'
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['PUT'])
def recover_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'WORK'
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['PUT'])
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


@api_view(['POST'])
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
