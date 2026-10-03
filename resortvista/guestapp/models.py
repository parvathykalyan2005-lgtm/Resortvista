from django.db import models

# Create your models here.
class tbl_resortowner(models.Model):
    owner_id = models.AutoField(primary_key=True)
    owner_name = models.CharField(max_length=100)
    owner_email = models.CharField(max_length=191, unique=True)
    owner_phone = models.CharField(max_length=15)
    licence_image = models.ImageField(upload_to='images/', null=True, blank=True)
    location_id = models.IntegerField(null=True, blank=True)
    registration_date = models.DateField(auto_now_add=True)
    login_id = models.ForeignKey('tbl_login', on_delete=models.CASCADE, null=True, blank=True, unique=True)

class tbl_login(models.Model):
    login_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    role = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default='pending')

class tbl_customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100)
    customer_email = models.CharField(max_length=191, unique=True)
    customer_phone = models.CharField(max_length=15)
    address = models.TextField()
    location_id = models.IntegerField(null=True, blank=True)
    login_id = models.ForeignKey('tbl_login', on_delete=models.CASCADE, null=True, blank=True, unique=True)
