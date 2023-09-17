from django.shortcuts import render, redirect
from django.db import connection
from django.urls import reverse

from app import models


def get_modeling_detailed_page(request, id):
    return render(request, 'modeling_more_detailed.html', {
        'modeling' : models.TypesOfModeling.objects.filter(modeling_id=id).first()
    })


def search_modeling(request):
    query = request.GET.get('q')
    if query:
        search_results = {'modeling': []}

        for item in models.TypesOfModeling.objects.all():
            if query.lower() in item.modeling_name.lower():
                search_results['modeling'].append(item)
    
    else:
        search_results = {'modeling': models.TypesOfModeling.objects.all()}
    return render(request, 'types_modeling.html', {'init_data' : search_results } )


def delete_modeling(id):
    try:
        with connection.cursor() as cursor:
            if '\'' in id:
                return False
            quarry = f"UPDATE types_of_modeling SET modeling_status = 'DELE' WHERE modeling_id = %s"
            cursor.execute(quarry, [id])
            connection.commit()
            
            return True
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        return False
    

def update_modeling_list_page(request, id):
    if not delete_modeling(id):
        pass
    return redirect(reverse('search_modeling'))
