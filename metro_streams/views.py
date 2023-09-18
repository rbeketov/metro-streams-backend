from django.shortcuts import render

data_modeling = {
    'modeling': [
        {
            'id': 0,
            'type': 'Модели очередей',
            'description': 'Эти модели используются для анализа и прогнозирования длин очередей на станциях метро и на платформах. Модели Марковских процессов могут быть полезными для оценки времени ожидания и загруженности.',
            'image_url': 'images/queue_model.jpeg'
        },
        {
            'id': 1,
            'type': 'Модели сетевого потока',
            'description': 'Эти модели описывают поток пассажиров и поездов через сеть метро. Модели сетевого потока могут использоваться для оптимизации маршрутов и расписаний движения поездов.',
            'image_url': 'images/network_model.jpeg'
        },
        {
            'id': 2,
            'type': 'Симуляционные модели',
            'description': 'Симуляционные модели позволяют имитировать движение пассажиров и поездов в метро на компьютере. Это может быть полезно для анализа различных сценариев и оценки эффективности изменений в системе метро.',
            'image_url': 'images/simulation_model.jpeg'
        },
        {
            'id': 3,
            'type': 'Графовые модели',
            'description': 'Графовые модели могут быть использованы для моделирования структуры и связей между станциями, линиями и узлами метро. Это может помочь в анализе эффективности сети и выявлении слабых мест.',
            'image_url': 'images/graph_model.jpeg'
        },
        {
            'id': 4,
            'type': 'Статистические модели',
            'description': 'Статистические модели могут использоваться для анализа и прогнозирования пассажиропотока на основе исторических данных, климатических условий, событий и других факторов.',
            'image_url': 'images/statistic_model.jpeg'
        },
        {
            'id': 5,
            'type': 'Операционные модели',
            'description': 'Эти модели ориентированы на оптимизацию операций метро, такие как управление поездами, расписание движения, а также ассортимент и количество поездов.',
            'image_url': 'images/operation_model.jpeg'
        },
        
    ]
}



# def GetTypesAnalysisPage(request):
#     return render(request, 'types_modeling.html', {'init_data' : data_modeling } )


def GetModelingDetailedPage(request, id):
    data_by_id = data_modeling.get('modeling')[id]
    return render(request, 'modeling_more_detailed.html', {
        'modeling': data_by_id
    })


def SearchModeling(request):
    query = request.GET.get('q')
    if query:
        search_results = {'modeling': []}

        for item in data_modeling['modeling']:
            if query.lower() in item['type'].lower():
                search_results['modeling'].append(item)
    
    else:
        query = ''
        search_results = data_modeling
    return render(request, 'types_modeling.html', {'init_data' : search_results , 'search_value': query} )