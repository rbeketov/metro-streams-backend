from django.db import models


class ApplicationsForModeling(models.Model):
    application_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    date_application_create = models.DateField()
    date_application_accept = models.DateField(blank=True, null=True)
    date_application_complete = models.DateField(blank=True, null=True)
    status_application = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'applications_for_modeling'


class ModelingApplications(models.Model):
    modeling = models.OneToOneField('TypesOfModeling', models.DO_NOTHING, primary_key=True)  # The composite primary key (modeling_id, application_id) found, that is not supported. The first column is selected.
    application = models.ForeignKey(ApplicationsForModeling, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'modeling_applications'
        unique_together = (('modeling', 'application'),)


class TypesOfModeling(models.Model):
    modeling_id = models.AutoField(primary_key=True)
    modeling_name = models.CharField(max_length=30)
    modeling_description = models.CharField(max_length=1000)
    modeling_price = models.DecimalField(max_digits=30, decimal_places=2)
    modeling_image_url = models.CharField(max_length=40)
    modeling_status = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'types_of_modeling'


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=20)
    second_name = models.CharField(max_length=20)
    email = models.CharField(unique=True, max_length=30)
    login = models.CharField(unique=True, max_length=30)
    password = models.CharField(unique=True, max_length=30)
    role = models.CharField()

    class Meta:
        managed = False
        db_table = 'users'