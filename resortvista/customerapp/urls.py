from django.urls import path
from . import views

urlpatterns = [
    path('customerindex/', views.customerindex, name='customerindex'),
    path('resortview/', views.resortview, name='resortview'),
    path('resortsingleview/<int:resort_id>/', views.resortsingleview, name='resortsingleview'),
    path('availability/<int:resort_id>/', views.check_availability, name='check_availability'),
    path('availability/<int:resort_id>/ajax/', views.check_availability_ajax, name='check_availability_ajax'),
    path('booking/<int:resort_id>/', views.booking, name='booking'),
    path('customizepackages/<int:resort_id>/', views.customize_packages, name='customize_packages'),
    path('multiplepackagecustomization/<int:resort_id>/', views.customize_packages, name='multiple_package_customization'),  
    path('payment/', views.payment, name='payment'),
    path('mybookings/', views.mybookings, name='mybookings'),
    path('about/', views.aboutc, name='aboutc'),
    path('contact/', views.contactc, name='contactc'),
    
]