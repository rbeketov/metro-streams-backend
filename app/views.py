from datetime import datetime, timedelta

import requests
import json
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.utils.text import slugify

from app.serializers import TypesOfModelingSerializer
from app.serializers import ModelingApplicationsSerializer
from app.serializers import ApplicationsForModelingSerializer
from app.serializers import UsersSerializer
from app.serializers import DetailsOfModelingSerializer

from app.models import TypesOfModeling
from app.models import ModelingApplications
from app.models import ApplicationsForModeling
from app.models import Users


from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser


from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.http import HttpRequest

from django.db.models import Q, F
from drf_yasg import openapi


import hashlib
import secrets

from app.s3 import delete_image_from_s3, upload_image_to_s3, get_image_from_s3

from app.redis_view import (
    set_key,
    get_value,
    delete_value
)

USER_ID = 5
MODERATOR_ID = 6


def check_authorize(request):
    response = login_view_get(request._request)
    if response.status_code == 200:
        user = Users.objects.get(user_id=response.data.get('user_id'))
        return user
    return None


#ser Domain
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['first_name', 'second_name', 'email', 'login', 'password'],
        properties={
            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя пользователя'),
            'second_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия пользователя'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Электронная почта пользователя'),
            'login': openapi.Schema(type=openapi.TYPE_STRING, description='Логин пользователя'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя'),
        }
    ),
    responses={
        201: openapi.Response(description='Пользователь успешно создан'),
        400: openapi.Response(description='Не хватает обязательных полей или пользователь уже существует'),
    },
    operation_description='Регистрация нового пользователя',
)
@api_view(['POST'])
def registration(request, format=None):
    required_fields = ['first_name', 'second_name', 'email', 'login', 'password']
    missing_fields = [field for field in required_fields if field not in request.data]

    if missing_fields:
        return Response({'Ошибка': f'Не хватает обязательных полей: {", ".join(missing_fields)}'}, status=status.HTTP_400_BAD_REQUEST)

    if Users.objects.filter(email=request.data['email']).exists() or Users.objects.filter(login=request.data['login']).exists():
        return Response({'Ошибка': 'Пользователь с таким email или login уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    password_hash = hashlib.sha256(f'{request.data["password"]}'.encode()).hexdigest()

    Users.objects.create(
        first_name=request.data['first_name'],
        second_name=request.data['second_name'],
        email=request.data['email'],
        login=request.data['login'],
        password=password_hash,
        role='USR',
    )
    return Response(status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'login': openapi.Schema(type=openapi.TYPE_STRING, description='Логин пользователя'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя'),
        },
        required=['login', 'password'],
    ),
    responses={
        200: openapi.Response(description='Успешная авторизация', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'user_id': openapi.Schema(type=openapi.TYPE_INTEGER)})),
        400: openapi.Response(description='Неверные параметры запроса или отсутствуют обязательные поля'),
        401: openapi.Response(description='Неавторизованный доступ'),
    },
    operation_description='Метод для авторизации',
)
@api_view(['POST'])
def login_view(request, format=None):
    existing_session = request.COOKIES.get('session_key')
    # print(existing_session)
    if existing_session and get_value(existing_session):
        return Response({'user_id': get_value(existing_session)})

    login_ = request.data.get("login")
    password = request.data.get("password")
    
    if not login_ or not password:
        return Response({'error': 'Необходимы логин и пароль'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = Users.objects.get(login=login_)
    except Users.DoesNotExist:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    password_hash = hashlib.sha256(f'{password}'.encode()).hexdigest()

    if password_hash == user.password:
        random_part = secrets.token_hex(8)
        session_hash = hashlib.sha256(f'{user.user_id}:{login_}:{random_part}'.encode()).hexdigest()
        set_key(session_hash, user.user_id)

        serialize = UsersSerializer(user)
        response = JsonResponse(serialize.data)
        response.set_cookie('session_key', session_hash, max_age=86400)
        return response

    return Response(status=status.HTTP_401_UNAUTHORIZED)



def login_view_get(request):
    existing_session = request.COOKIES.get('session_key')
    if existing_session and get_value(existing_session):
        return Response({'user_id': get_value(existing_session)})
    return Response(status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(description='Успешный выход', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})),
        401: openapi.Response(description='Неавторизованный доступ', schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    },
    operation_description='Метод для выхода пользователя из системы',
)
@api_view(['GET'])
def logout_view(request):
    session_key = request.COOKIES.get('session_key')
    # print(session_key)
    if session_key:
        if not get_value(session_key):
            return JsonResponse({'error': 'Вы не авторизованы'}, status=status.HTTP_401_UNAUTHORIZED)
        delete_value(session_key)
        response = JsonResponse({'message': 'Вы успешно вышли из системы'})
        response.delete_cookie('session_key')
        return response
    else:
        return JsonResponse({'error': 'Вы не авторизованы'}, status=status.HTTP_401_UNAUTHORIZED)


# support func
def filter_applications(status_filter, date_start, date_end, user):
    if not user:
        applications = ApplicationsForModeling.objects.exclude(status_application__in=['DELE', 'DRFT'])
    else:
        applications = ApplicationsForModeling.objects.filter(
            Q(user=user)
        ).exclude(status_application__in=['DELE', 'DRFT'])

    if status_filter:
        applications = applications.filter(Q(status_application=status_filter))
    if date_start:
        applications = applications.filter(Q(date_application_create__gte=date_start))
    if date_end:
        applications = applications.filter(Q(date_application_create__lte=date_end))

    return applications


# Domain ApplicationsForModeling
@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('status',
                          openapi.IN_QUERY,
                          description="Статус заявки для фильтрации",
                          type=openapi.TYPE_STRING),
        openapi.Parameter('date_start',
                          openapi.IN_QUERY,
                          description="Нижняя граница даты создания заявки для фильтрации",
                          type=openapi.TYPE_STRING,
                          format=openapi.FORMAT_DATE),
        openapi.Parameter('date_end',
                          openapi.IN_QUERY,
                          description="Верхняя граница даты создания заявки для фильтрации",
                          type=openapi.TYPE_STRING,
                          format=openapi.FORMAT_DATE),
    ]
)
@api_view(['GET'])
def search_applications(request, format=None):
    user = check_authorize(request)
    if not user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    status_filter = request.GET.get('status')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    usr = user if user.role == 'USR' else None

    if date_start and date_end:
        date_start = datetime.strptime(date_start, "%Y-%m-%d") + timedelta(hours=0, minutes=0, seconds=0)
        date_end = datetime.strptime(date_end, "%Y-%m-%d") + timedelta(hours=0, minutes=0, seconds=0)

    applications = filter_applications(status_filter, date_start, date_end, usr)

    applications = applications.annotate(
        user_first_name=F('user__first_name'),
        user_second_name=F('user__second_name'),
        moderator_first_name=F('moderator__first_name'),
        moderator_second_name=F('moderator__second_name'),
        moderator_email=F('moderator__email'),
    )

    serializer = ApplicationsForModelingSerializer(applications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="Получить детали заявки",
)
@api_view(['GET'])
def get_application(request, pk, format=None):
    user = check_authorize(request)
    if not user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    for_check = ApplicationsForModeling.objects.filter(
        Q(application_id=pk) & Q(user=user)
    )
    if (not user.role == 'MOD' and not for_check):
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        applications = ApplicationsForModeling.objects.filter(application_id=pk).annotate(
            user_email=F('user__email'),
            user_first_name=F('user__first_name'),
            user_second_name=F('user__second_name'),
            moderator_email=F('moderator__email'),
            moderator_first_name=F('moderator__first_name'),
            moderator_second_name=F('moderator__second_name')
        ).values(
            'modelingapplications__modeling__modeling_id',
            'modelingapplications__modeling__modeling_name',
            'modelingapplications__modeling__modeling_description',
            'modelingapplications__result_modeling',
            'people_per_minute',
            'time_interval',
            'date_application_create',
            'date_application_accept',
            'date_application_complete',
            'status_application',
            'modelingapplications__modeling__modeling_price',
            'modelingapplications__modeling__modeling_image_url',
            'user_id',
            'user_first_name',
            'user_second_name',
            'user_email',
            'moderator_id',
            'moderator_first_name',
            'moderator_second_name',
            'moderator_email'
        )

        if applications:
            modeling_data_list = []

            for application in applications:
                modeling_data = {
                    'modeling_id': application['modelingapplications__modeling__modeling_id'],
                    'modeling_name': application['modelingapplications__modeling__modeling_name'],
                    'modeling_description': application['modelingapplications__modeling__modeling_description'],
                    'modeling_price': application['modelingapplications__modeling__modeling_price'],
                    'modeling_image_url': application['modelingapplications__modeling__modeling_image_url'],
                    'modeling_result' : application['modelingapplications__result_modeling'],
                }
                modeling_data_list.append(modeling_data)

            application_data = {
                'people_per_minute': applications[0]['people_per_minute'],
                'time_interval': applications[0]['time_interval'],
                'date_application_create': applications[0]['date_application_create'],
                'date_application_accept': applications[0]['date_application_accept'],
                'date_application_complete': applications[0]['date_application_complete'],
                'status_application': applications[0]['status_application'],
            }

            user_data = {
                'user_id': applications[0]['user_id'],
                'first_name': applications[0]['user_first_name'],
                'second_name': applications[0]['user_second_name'],
                'email': applications[0]['user_email']
            }

            moderator_data = {
                'moderator_id': applications[0]['moderator_id'],
                'first_name': applications[0]['moderator_first_name'],
                'second_name': applications[0]['moderator_second_name'],
                'email': applications[0]['moderator_email']
            }

            response_json = {
                'application_id': pk,
                'application_data': application_data,
                'user_data': user_data,
                'moderator_data': moderator_data,
                'modeling': modeling_data_list
            }

            return Response(response_json, status=status.HTTP_200_OK)
        else:
            return Response({"Ошибка": "Заявки с таким id не существует"}, status=status.HTTP_404_NOT_FOUND)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"Ошибка": "Заявки с таким id не существует"}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новый статус заявки",
                enum=[  "COMP", "CANC"],
            ),
        },
        required=['status'],
    ),
    responses={
        200: "Успешно обновлен статус заявки",
        400: "Неверный запрос",
    },
    operation_description="Изменить статус заявки",
)
@api_view(['PUT'])
def moderator_set_status_application(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            new_status = data['status']
        else:
            return Response({"Ошибка": "\'status\' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in ['COMP', 'CANC']:
            return Response({"Ошибка": "Указан недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)

        valid_transitions = {
            'WORK': ['COMP', 'CANC'],
        }

        current_status = application.status_application

        if new_status not in valid_transitions.get(current_status, []):
            return Response(
                {"error": f"Невозможно сменить статус с {current_status} на {new_status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if application.status_application != new_status:
            application.status_application = new_status
            application.save()
            request_for_get_application = HttpRequest()
            request_for_get_application.method = 'GET'
            response = get_application(request_for_get_application, pk)
            return Response(response.data, status=status.HTTP_200_OK)
        else:
            return Response({"Ошибка": f"Заявка {pk} уже имеет {new_status}"}, status=status.HTTP_400_BAD_REQUEST)

    except ApplicationsForModeling.DoesNotExist:
        return Response({"Ошибка": "Заявка не найдена"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"Ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новый статус заявки",
                enum=["WORK", "CANC"],
            ),
        },
        required=['status'],
    ),
    responses={
        200: "Успешно обновлен статус заявки",
        400: "Неверный запрос",
    },
    operation_description="Изменить статус заявки",
)
@api_view(['PUT'])
def user_set_status(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'USR':
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            new_status = data['status']
        else:
            return Response({"Ошибка": "\'status\' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in ['WORK']:
            return Response({"Ошибка": "Указан недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status == 'WORK' and ( not data['people_per_minute'] or not data['time_interval']):
            return Response({"Ошибка": "Не переданы параметры моделирования"}, status=status.HTTP_400_BAD_REQUEST)

        valid_transitions = {
            'DRFT': ['WORK'],
        }

        current_status = application.status_application

        if new_status not in valid_transitions.get(current_status, []):
            return Response(
                {"error": f"Невозможно сменить статус с {current_status} на {new_status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if application.status_application != new_status:
            application.status_application = new_status

            if new_status == 'WORK':
                try:
                    modelings = ModelingApplications.objects.filter(application=application)
                    post_url = "http://localhost:8080/calculate-stream/"
            
                    calc_req_data = {
                        "id": application.application_id,
                        "time_interval": application.time_interval,
                        "people_per_minute": application.people_per_minute,
                        "modelings": [
                            {"model_id": modeling.modeling.modeling_id, "load": modeling.modeling.load} for modeling in modelings
                        ],
                    }

                    response_post = requests.post(post_url, json=calc_req_data)
                    response_post.raise_for_status()
                    application.date_application_create = timezone.now()
                except Exception as e:
                    print(e)

            application.save()
            return Response(status=status.HTTP_200_OK)

            
        else:
            return Response({"Ошибка": f"Заявка {pk} уже имеет {new_status}"}, status=status.HTTP_400_BAD_REQUEST)

    except ApplicationsForModeling.DoesNotExist:
        return Response({"Ошибка": "Заявка не найдена"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"Ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@parser_classes([JSONParser])
def write_modeling_result(request, format=None):
    try:
        data = request.data
        if not data["token"] or data["token"] != "Hg12HdEdEiid9-djEDegE":
            return Response(status=status.HTTP_403_FORBIDDEN)

        application_id = data["application_id"]
        for result_data in data["results"]:
            modeling_id = result_data["model_id"]

            modeling = ModelingApplications.objects.filter(application=application_id, modeling=modeling_id)

            if modeling:
                modeling.update(result_modeling=result_data["output_load"])

        application = ApplicationsForModeling.objects.get(pk=application_id)
        application.date_application_accept = timezone.now()
        application.save()

        return Response(status=status.HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='DELETE',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новый статус заявки",
                enum=["DELE"],
            ),
        },
        required=['status'],
    ),
    responses={
        200: "Успешно обновлен статус заявки",
        400: "Неверный запрос",
    },
    operation_description="Удалить черновик",
)
@api_view(['DELETE'])
def user_delete_application(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'USR':
        print("a?")
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        application = ApplicationsForModeling.objects.get(pk=pk)

        current_status = application.status_application

        if current_status != 'DRFT':
            return Response(
                {"error": f"удалить можно, только черновую заявку"},
                status=status.HTTP_400_BAD_REQUEST
            )
       
        application.status_application = 'DELE'
        application.save()

        return Response(status=status.HTTP_200_OK)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"Ошибка": "Заявка не найдена"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"Ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'modeling_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="ID услуги для удаления из заявки",
            ),
        },
        required=['modeling_id'],
    ),
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="Удалить услугу из заявки",
)
@api_view(['DELETE'])
def del_modeling_from_application(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'USR':
        return Response(status=status.HTTP_403_FORBIDDEN)

    
    application = ApplicationsForModeling.objects.filter(
        Q(application_id=pk) & Q(user=user)
    ).first()

    if not application:
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        modeling_id = request.data.get('modeling_id')

        if modeling_id is None:
            return Response({"error": "Поле 'modeling_id' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)
        
        modeling_application = ModelingApplications.objects.get(
            application=application, modeling=modeling_id
        )

        if modeling_application:
            modeling_application.delete()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({"error": "Запрошеная услуга не найдена в заявке"}, status=status.HTTP_404_NOT_FOUND)
    except ApplicationsForModeling.DoesNotExist:
        return Response({"error": "Такая заявка не существует"}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'modeling_id': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="ID услуги для изменения результата моделирования",
            ),
            'new_result': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                format=openapi.FORMAT_DOUBLE,
                description="Новое значение результата моделирования",
            ),
        },
        required=['modeling_id', 'new_result'],
    ),
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="Изменить данные результата моделирования в заявке",
)
@api_view(['PUT'])
def edit_result_modeling_in_application(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        modeling_id = request.data.get('modeling_id')
        new_result = request.data.get('new_result')

        modeling_application = ModelingApplications.objects.filter(application_id=pk, modeling_id=modeling_id).first()

        if modeling_application:
            modeling_application.result_modeling = new_result
            modeling_application.save()
            return Response("Успешно", status=status.HTTP_200_OK)
        else:
            return Response("Не найдено", status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'people_per_minute': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Новое значение для 'people_per_minute'",
            ),
            'time_interval': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Новое значение для 'time_interval'",
            ),
        },
        required=['people_per_minute', 'time_interval'],
    ),
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="Изменить 'people_per_minute' и 'time_interval' в заявке",
)
@api_view(['PUT'])
def update_applications(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'USR':
        return Response(status=status.HTTP_403_FORBIDDEN)

    application = ApplicationsForModeling.objects.filter(
        Q(application_id=pk) & Q(user=user)
    ).first()

    if not application:
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        # application = ApplicationsForModeling.objects.get(pk=pk)
        people_per_minute = request.data.get('people_per_minute')
        time_interval = request.data.get('time_interval')
        application.people_per_minute = people_per_minute
        application.time_interval = time_interval
        application.save()

        return Response("Успешно", status=status.HTTP_200_OK)

    except ApplicationsForModeling.DoesNotExist:
        return Response("Не найдено", status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


# Domain TypeOfModeling
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'modeling_id': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
            ),
        },
        required=['modeling_id'],
    ),
    responses={
        201: "Успешное добавление модели в заявку",
        400: "Неверный запрос",
    },
    operation_description="Добавление модели в последнюю черновую заявку",
)
@api_view(['POST'])
def add_modeling_to_applications(request, format=None):
    user = check_authorize(request)
    if not user or user.role != 'USR':
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        data = request.data

        if 'modeling_id' not in data:
            raise KeyError(f"Объект моделирования отсутствует в запросе")

        usr_id = user.user_id
        modeling_id = data['modeling_id']

        application = ApplicationsForModeling.objects.filter(
            user_id=usr_id,
            status_application='DRFT'
        ).first()

        if not application:
            application = ApplicationsForModeling.objects.create(
                user=user,
                status_application='DRFT',
                date_application_create=timezone.now()
            )
        else:
            modeling_application = ModelingApplications.objects.filter(
                modeling_id=modeling_id,
                application=application
            ).first()

            if modeling_application:
                return Response(
                    {"error": f"Модель с ID {modeling_id} уже существуют в заявке"},
                    status=status.HTTP_409_CONFLICT
                )

        modeling_application = ModelingApplications.objects.create(
            modeling_id=modeling_id,
            application=application
        )

        response_data = {
            "draft_id" : application.application_id
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"Ошибка": str(e)}, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='GET',
    manual_parameters=[
        openapi.Parameter(
            'name',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description='Поиск по названию моделирования (case-insensitive)',
            required=False
        ),
        openapi.Parameter(
            'price_under',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_NUMBER,
            description='Минимальная цена моделирования',
            required=False
        ),
        openapi.Parameter(
            'price_upper',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_NUMBER,
            description='Максимальная цена моделирования',
            required=False
        ),
    ],
    responses={
        200: "Успешно",
    },
    operation_description="Поиск моделирований с фильтрацией по названию и цене",
)
@api_view(['GET'])
def search_modeling(request, format=None):
    user = check_authorize(request)
    show_withdraw = (user and user.role == 'MOD')
    get_draw = (user and user.role == 'USR')
    
    response_drft = None
    
    if get_draw:
        application = ApplicationsForModeling.objects.filter(
            user_id=user.user_id,
            status_application='DRFT'
        ).first()
        if application:
            response_drft = application.application_id

    if show_withdraw:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") |
            Q(modeling_status="WITH")
        )
    else:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK")
        )

    query_name = request.GET.get('name')
    price_under = request.GET.get('price_under')
    price_upper = request.GET.get('price_upper')

    if query_name:
        modeling_objects = modeling_objects.filter(
            Q(modeling_name__icontains=query_name.lower())
        )
    if price_under:
        modeling_objects = modeling_objects.filter(
            Q(modeling_price__gte=price_under)
        )
    if price_upper:
        modeling_objects = modeling_objects.filter(
            Q(modeling_price__lte=price_upper)
        )

    serializer = TypesOfModelingSerializer(modeling_objects, many=True)
    response_data = {
        'draft_id': response_drft,
        'modeling_objects': serializer.data
    }
    return Response(response_data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="оплучить информацию о модели по ID",
)
@api_view(['GET'])
def get_type_modeling(request, pk, format=None):
    user = check_authorize(request)

    modeling_object = TypesOfModeling.objects.filter(
        Q(modeling_id=pk)
    ).first()

    if (
        not modeling_object or
        modeling_object.modeling_status == 'DELE' or
        (
            modeling_object.modeling_status == 'WITH' and
            not(user and user.role == "MOD")   
        )
    ):
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = DetailsOfModelingSerializer(modeling_object)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    responses={
        200: "Успешно",
        400: "Ошибка: можно отозвать только объект моделирования \'в работе\'",
        404: "Не найдено",
    },
    operation_description="Отзыв услуги по ID",
)
@api_view(['PUT'])
def withdraw_type_modeling(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    if modeling_object.modeling_status == "WORK":
        modeling_object.modeling_status = 'WITH'
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    responses={
        200: "Успешно",
        400: "Ошибка: можно восстановить только отозванный объект моделирования",
        404: "Не найден объект моделирования",
    },
    operation_description="Восстановить объект моделирования по ID",
)
@api_view(['PUT'])
def recover_type_modeling(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    if modeling_object.modeling_status == "WITH":
        modeling_object.modeling_status = 'WORK'
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='delete',
    responses={
        200: "Успешно",
        400: "Ошибка: нельзя удалить объект моделирования \'в работе\'",
        404: "Не найден объект моделирования",
    },
    operation_description="Удалить объект моделирования по ID",
)
@api_view(['DELETE'])
def delete_type_modeling(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    if modeling_object.modeling_status == "WITH":
        modeling_object.modeling_status = 'DELE'
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'modeling_name': openapi.Schema(type=openapi.TYPE_STRING, description="Новое название моделирования"),
            'modeling_description': openapi.Schema(type=openapi.TYPE_STRING, description="Новое описание моделирования"),
            'modeling_price': openapi.Schema(type=openapi.TYPE_NUMBER, description="Новая цена моделирования"),
            'image': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY, description="The new modeling image data"),
            'load': openapi.Schema(type=openapi.TYPE_INTEGER, description="Новое значение нагрузки моделирования"),
        },
    ),
    responses={
        200: "Успешно",
        400: "Неверный запрос",
    },
    operation_description="Изменить объект моделирования по его ID",
)
@api_view(['PUT'])
def edit_type_modeling(request, pk, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    try:
        data = request.data

        modeling_object.modeling_name = data.get('modeling_name', modeling_object.modeling_name)
        modeling_object.modeling_description = data.get('modeling_description', modeling_object.modeling_description)
        modeling_object.modeling_price = data.get('modeling_price', modeling_object.modeling_price)
        modeling_object.load = data.get('load', modeling_object.load)

        if 'image' in data:
            old_image_path = modeling_object.modeling_image_url
            delete_image_from_s3(old_image_path)
            
            new_image_path = modeling_object.modeling_name + '.jpg'
            image_data = data['image']
            upload_image_to_s3(image_data, new_image_path, 'image/jpeg')
            modeling_object.modeling_image_url = new_image_path
       
        modeling_object.save()

        modeling_object.refresh_from_db()
        serializer = TypesOfModelingSerializer(modeling_object)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'modeling_name': openapi.Schema(type=openapi.TYPE_STRING, description="The name of the modeling"),
            'modeling_description': openapi.Schema(type=openapi.TYPE_STRING, description="The description of the modeling"),
            'modeling_price': openapi.Schema(type=openapi.TYPE_NUMBER, description="The price of the modeling"),
            'image': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY, description="The binary image data"),
            'load': openapi.Schema(type=openapi.TYPE_INTEGER, description="The URL of the modeling image"),
        },
        required=['modeling_name', 'modeling_price', 'load'],
    ),
    responses={
        201: "Successfully created modeling object",
        400: "Bad Request",
    },
    operation_description="Create a new modeling object",
)
@api_view(['POST'])
def create_type_modeling(request, format=None):
    user = check_authorize(request)
    if not user or user.role != 'MOD':
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        data = request.data

        modeling_name = data.get('modeling_name')
        modeling_description = data.get('modeling_description')
        modeling_price = data.get('modeling_price')
        image_data = data.get('image')
        load = data.get('load')

        modeling_name_for_path = slugify(modeling_name.split(' ', 1)[1])
        image_path = modeling_name_for_path + '.jpg'

        upload_image_to_s3(image_data, image_path, 'image/jpeg')

        new_modeling_object = TypesOfModeling(
            modeling_name=modeling_name,
            modeling_description=modeling_description,
            modeling_price=modeling_price,
            modeling_image_url=image_path,
            load=load
        )

        new_modeling_object.save()

        created_modeling_object = TypesOfModeling.objects.get(pk=new_modeling_object.pk)
        serializer = TypesOfModelingSerializer(created_modeling_object)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)
