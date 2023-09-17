from django.shortcuts import render

from app import models


def GetModelingDetailedPage(request, id):
    return render(request, 'modeling_more_detailed.html', {
        'modeling' : models.TypesOfModeling.objects.filter(modeling_id=id).first()
    })


def SearchModeling(request):
    query = request.GET.get('q')
    if query:
        search_results = {'modeling': []}

        for item in models.TypesOfModeling.objects.all():
            if query.lower() in item.modeling_name.lower():
                search_results['modeling'].append(item)
    
    else:
        search_results = {'modeling': models.TypesOfModeling.objects.all()}
    return render(request, 'types_modeling.html', {'init_data' : search_results } )