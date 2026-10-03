from django.db import models

from adminapp.models import tbl_category, tbl_location
from guestapp.models import tbl_resortowner

# Create your models here.
class tbl_resort(models.Model):
    resort_id = models.AutoField(primary_key=True)
    resort_name = models.CharField(max_length=100)
    resort_address = models.CharField(max_length=255)
    resort_phone = models.CharField(max_length=15)
    resort_image = models.ImageField(upload_to='images/', null=True, blank=True)
    location_id = models.ForeignKey(tbl_location, on_delete=models.CASCADE, null=True, blank=True)
    owner_id = models.ForeignKey(tbl_resortowner,on_delete=models.CASCADE,null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='available')
    category_id = models.ForeignKey(tbl_category,on_delete=models.CASCADE, null=True, blank=True)

class tbl_package(models.Model):
    package_id = models.AutoField(primary_key=True)
    resort_id = models.ForeignKey('tbl_resort', on_delete=models.CASCADE, null=True, blank=True)
    package_name = models.CharField(max_length=100)
    package_image = models.ImageField(upload_to='images/', null=True, blank=True)
    duration = models.CharField(max_length=50)
    max_people = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default='available')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class tbl_packagedetails(models.Model):
    package_details_id = models.AutoField(primary_key=True)
    package_id = models.ForeignKey(tbl_package, on_delete=models.CASCADE)
    package_detail_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)



