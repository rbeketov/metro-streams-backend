from django.shortcuts import render

data_modeling = {'modeling' : [
                {'id': 0, 
                 'type' : 'Числовое моделирование',
                 'description' : 'Модели в виде дискретных аналогов интегралов, дифференциальных уравнений (разностные уравнения), интеграционные формулы'},
                {'id': 1,
                 'type' : 'Диаграммное моделирование',
                 'description' : 'Диграмма Фейнмана, Константинова - Переля, графы состояний CMO, диаграммы системной динамики, когнитивные карты'},
                {'id': 2,
                 'type' : 'Моделирование в виде математических формул',
                 'description' : 'Модели в виде формул, уравнений, систем линенйныйх уравнений и неравенств и т.п.'},
                ]}


def GetTypesAnalysisPage(request):
    return render(request, 'types_modeling.html', {'init_data' : data_modeling } )


def GetModelingDetailedPage(request, id):
    data_by_id = data_modeling.get('modeling')[id]
    return render(request, 'modeling_more_detailed.html', {
        'modeling': data_by_id
    })