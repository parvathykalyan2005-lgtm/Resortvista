from django.db import models

# Create your models here.
class tbl_packagecustomizerequest(models.Model):
    package_customize_id = models.AutoField(primary_key=True)
    package_id = models.ForeignKey('resortownerapp.tbl_package', on_delete=models.CASCADE, null=True, blank=True)
    customer_id = models.ForeignKey('guestapp.tbl_customer', on_delete=models.CASCADE, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
class tbl_customizeitem(models.Model):
    customize_item_id = models.AutoField(primary_key=True)
    package_customize_id = models.ForeignKey('tbl_packagecustomizerequest', on_delete=models.CASCADE, null=True, blank=True)
    package_details_id = models.ForeignKey('resortownerapp.tbl_packagedetails', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=50, default='Added', null=True, blank=True)
class tbl_booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    resort_id = models.ForeignKey('resortownerapp.tbl_resort', on_delete=models.CASCADE, null=True, blank=True)
    customer_id = models.ForeignKey('guestapp.tbl_customer', on_delete=models.CASCADE, null=True, blank=True)
    package_customize_id = models.ForeignKey('tbl_packagecustomizerequest', on_delete=models.CASCADE, null=True, blank=True)
    check_in_date = models.DateField(null=True, blank=True)
    check_out_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    booking_status = models.CharField(max_length=50, default='Pending', null=True, blank=True)
    package_id= models.ForeignKey('resortownerapp.tbl_package', on_delete=models.CASCADE, null=True, blank=True)
    payment_id = models.ForeignKey('tbl_payment', on_delete=models.CASCADE, null=True, blank=True)
    owner_id = models.ForeignKey('guestapp.tbl_resortowner', on_delete=models.CASCADE, null=True, blank=True)
class tbl_payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    booking_id = models.ForeignKey('tbl_booking', on_delete=models.CASCADE, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=50, default='Pending', null=True, blank=True)
    customer_id = models.ForeignKey('guestapp.tbl_customer', on_delete=models.CASCADE, null=True, blank=True)
    