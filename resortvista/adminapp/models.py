from django.db import models

# Create your models here.
class tbl_district(models.Model):
     district_id=models.AutoField(primary_key=True)
     district_name=models.CharField(max_length=50)

class tbl_category(models.Model):
     category_id=models.AutoField(primary_key=True)
     category_name=models.CharField(max_length=50)
     category_image=models.ImageField(upload_to='images/')

class tbl_location(models.Model):
     location_id=models.AutoField(primary_key=True)
     district_id=models.ForeignKey(tbl_district, on_delete=models.CASCADE)
     location_name=models.CharField(max_length=50)

