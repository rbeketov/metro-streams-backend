from datetime import datetime, timedelta

from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.utils.text import slugify


from app.serializers import TypesOfModelingSerializer
from app.serializers import ModelingApplicationsSerializer
from app.serializers import ApplicationsForModelingSerializer
from app.serializers import UsersSerializer

from app.models import TypesOfModeling
from app.models import ModelingApplications
from app.models import ApplicationsForModeling
from app.models import Users

from rest_framework.decorators import api_view
from rest_framework.decorators import action

from django.http import HttpRequest

from django.utils import timezone
from django.db import connection
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce
from drf_yasg import openapi

from enum import Enum

from app.s3 import delete_image_from_s3, upload_image_to_s3, get_image_from_s3


class UsersENUM(Enum):
    USER_ID = 1
    MODERATOR_ID = 2



# Domain Users
    # in process

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
    status_filter = request.GET.get('status')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    if date_start and date_end:
        date_start = datetime.strptime(date_start, "%Y-%m-%d") + timedelta(hours=0, minutes=0, seconds=0)
        date_end = datetime.strptime(date_end, "%Y-%m-%d") + timedelta(hours=0, minutes=0, seconds=0)


    if status_filter and date_start and date_end:
        applications = ApplicationsForModeling.objects.filter(
            Q(status_application=status_filter) &
            Q(date_application_create__gte=date_start) &
            Q(date_application_create__lte=date_end)
        )
    elif status_filter and date_start:
        applications = ApplicationsForModeling.objects.filter(
            Q(status_application=status_filter) &
            Q(date_application_create__gte=date_start)
        )
    elif status_filter and date_start:
        applications = ApplicationsForModeling.objects.filter(
            Q(status_application=status_filter) &
            Q(date_application_create__gte=date_end)
        )
    elif date_start and date_end:
        applications = ApplicationsForModeling.objects.filter(
            Q(date_application_create__gte=date_start) &
            Q(date_application_create__lte=date_end)
        )
    elif date_start:
        applications = ApplicationsForModeling.objects.filter(
            Q(date_application_create__gte=date_start)
        )
    elif date_end:
        applications = ApplicationsForModeling.objects.filter(
            Q(date_application_create__lte=date_end)
        )
    else:
        applications = ApplicationsForModeling.objects.all()

    applications = applications.annotate(
        user_first_name=F('user__first_name'),
        user_second_name=F('user__second_name'),
        moderator_first_name=F('moderator__first_name'),
        moderator_second_name=F('moderator__second_name'),
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
    try:
        application = ApplicationsForModeling.objects.filter(application_id=pk).annotate(
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
        ).first()

        if application:
            user_data = {
                'user_id': application['user_id'],
                'first_name': application['user_first_name'],
                'second_name': application['user_second_name'],
                'email': application['user_email']
            }

            moderator_data = {
                'moderator_id': application['moderator_id'],
                'first_name': application['moderator_first_name'],
                'second_name': application['moderator_second_name'],
                'email': application['moderator_email']
            }

            modeling_data = {
                'modeling_id': application['modelingapplications__modeling__modeling_id'],
                'modeling_name': application['modelingapplications__modeling__modeling_name'],
                'modeling_description': application['modelingapplications__modeling__modeling_description'],
                'people_per_minute': application['people_per_minute'],
                'time_interval': application['time_interval'],
                'date_application_create': application['date_application_create'],
                'date_application_accept': application['date_application_accept'],
                'date_application_complete': application['date_application_complete'],
                'status_application': application['status_application'],
                'modeling_price': application['modelingapplications__modeling__modeling_price'],
                'modeling_image_url': application['modelingapplications__modeling__modeling_image_url'],
            }

            response_json = {
                'application_id': pk,
                'user_data': user_data,
                'moderator_data': moderator_data,
                'modeling': [modeling_data]
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
                enum=["WORK", "COMP", "CANC"],
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
    try:
        # check authorization
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            new_status = data['status']
        else:
            return Response({"Ошибка": "\'status\' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in ['WORK', 'COMP', 'CANC']:
            return Response({"Ошибка": "Указан недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)

        valid_transitions = {
            'DRFT': ['WORK'],
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
                enum=["ORDR", "CANC"],
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
def user_edit_application(request, pk, format=None):
    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            new_status = data['status']
        else:
            return Response({"Ошибка": "\'status\' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in ['ORDR', 'CANC']:
            return Response({"Ошибка": "Указан недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)

        valid_transitions = {
            'DRFT': ['ORDR'],
            'ORDE': ['CANC'],
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
    try:
        data = request.data
        application = ApplicationsForModeling.objects.get(pk=pk)

        if 'status' in data:
            new_status = data['status']
        else:
            return Response({"Ошибка": "\'status\' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in ['DELE']:
            return Response({"Ошибка": "Указан недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)

        valid_transitions = {
            'DRFT': ['DELE'],
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
    try:
        application = ApplicationsForModeling.objects.get(pk=pk)
        modeling_id = request.data.get('modeling_id')

        if modeling_id is None:
            return Response({"error": "Поле 'modeling_id' отсутствует в теле запроса"}, status=status.HTTP_400_BAD_REQUEST)

        modeling_application = ModelingApplications.objects.filter(
            application=application, modeling_id=modeling_id).first()

        if modeling_application:
            modeling_application.delete()
            request_for_get_application = HttpRequest()
            request_for_get_application.method = 'GET'
            response = get_application(request_for_get_application, pk)
            return Response(response.data, status=status.HTTP_200_OK)
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
    try:
        application = ApplicationsForModeling.objects.get(pk=pk)
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
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'modeling_id': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
            ),
        },
        required=['user_id', 'modeling_id'],
    ),
    responses={
        201: "Успешное добавление модели в заявку",
        400: "Неверный запрос",
    },
    operation_description="Добавление модели в последнюю заявку",
)
@api_view(['POST'])
def add_modeling_to_applications(request, format=None):
    try:
        data = request.data

        required_fields = ['user_id', 'modeling_id']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Поле '{field}' отсутствует в теле запроса")

        if not isinstance(data['modeling_id'], list):
            raise TypeError("Ошибка, 'modeling_id' должно быть типа list")

        user_id = UsersENUM.USER_ID
        modeling_ids = data['modeling_id']

        application = ApplicationsForModeling.objects.filter(
            user_id=user_id,
            status_application='DRFT'
        ).order_by('-date_application_create').first()

        if not application:
            raise RuntimeError("Нет ни одной созданной заявки")
        else:
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
                    {"Ошибка": f"Модель(модели) с ID {', '.join(map(str, conflict_models))} уже существуют в заявке"},
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
        return Response({"Ошибка": "Пользователь не найден"}, status=status.HTTP_400_BAD_REQUEST)
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
    query_name = request.GET.get('name')
    price_under = request.GET.get('price_under')
    price_upper = request.GET.get('price_upper')

    if query_name and price_under and price_upper:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_name__icontains=query_name.lower()) &
            Q(modeling_price__gte=price_under) &
            Q(modeling_price__lte=price_upper)
        )
    elif query_name and price_under:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_name__icontains=query_name.lower()) &
            Q(modeling_price__gte=price_under)
        )
    elif query_name and price_upper:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_name__icontains=query_name.lower()) &
            Q(modeling_price__lte=price_upper)
        )
    elif price_under and price_upper:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_price__gte=price_under) &
            Q(modeling_price__lte=price_upper)
        )
    elif query_name:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_name__icontains=query_name.lower())
        )
    elif price_under:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_price__gte=price_under)
        )
    elif price_upper:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK") &
            Q(modeling_price__lte=price_upper)
        )
    else:
        modeling_objects = TypesOfModeling.objects.filter(
            Q(modeling_status="WORK")
        )

    serializer = TypesOfModelingSerializer(modeling_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


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
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    serializer = TypesOfModelingSerializer(modeling_object)
    return Response(serializer.data)


@swagger_auto_schema(
    method='put',
    responses={
        200: "Успешно",
        404: "Не найдено",
    },
    operation_description="Отзыв услуги по ID",
)
@api_view(['PUT'])
def withdraw_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'DELE'
    modeling_object.save()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    responses={
        200: "Success",
        404: "Not Found",
    },
    operation_description="Recover a modeling object by ID",
)
@api_view(['PUT'])
def recover_type_modeling(request, pk, format=None):
    modeling_object = get_object_or_404(TypesOfModeling, pk=pk)
    modeling_object.modeling_status = 'WORK'
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
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)

