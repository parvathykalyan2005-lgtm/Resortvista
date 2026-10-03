from django.contrib import admin
from django.urls import include, path
from .import views

urlpatterns = [
    path('',views.index,name='guestindex'),
    path('resortownerreg/',views.resortownerreg,name='resortownerreg'),
    path('ajax_get_locations/', views.ajax_get_locations, name='ajax_get_locations'),
    path('login/',views.login,name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login_process/', views.login_process, name='login_process'),
    path('customerreg/',views.customerreg,name='customerreg'),
    path('choosereg/',views.choosereg,name='choosereg'),
    path('ajax_get_locations_customer/', views.ajax_get_locations_customer, name='ajax_get_locations_customer'),
    path('about/',views.about,name='guest_about'),
    path('contact/',views.contact,name='guest_contact'),
]