from django.contrib import admin

from app import models


admin.site.register(models.ApplicationsForModeling)
admin.site.register(models.ModelingApplications)
admin.site.register(models.Users)
admin.site.register(models.TypesOfModeling)