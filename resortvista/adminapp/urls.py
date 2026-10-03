from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
 path('message/', views.message, name='message'),
  path('profile/', views.profile, name='admin_profile'),
  path('districtreg/', views.districtreg ,name='districtreg'),
  path('viewdistrict/', views.viewdistrict, name='viewdistrict'),
  path('deldistrict/<id>', views.deletedistrict, name='deletedistrict'),
  path('editdistrict/<id>/', views.editdistrict, name="editdistrict"),
  path('categoryreg/', views.categoryreg, name="categoryreg"),
  path('viewcategory/', views.viewcategory, name='viewcategory'),
  path('editcategory/<id>/', views.editcategory, name="editcategory"),
  path('delcategory/<id>', views.deletecategory, name="deletecategory"),
  path('locationreg/', views.locationreg, name="locationreg"),
  path('locationview/', views.locationview, name="locationview"),
  path('admin_get_locations/', views.admin_get_locations, name='admin_get_locations'),
  path('editlocation/<id>/', views.editlocation, name="editlocation"),
  path('deletelocation/<id>', views.deletelocation, name="deletelocation"),
  path('ownerverify/', views.ownerverify, name='ownerverify'),
  path('acceptowner/<id>/', views.acceptowner, name='acceptowner'),
  path('deleteowner/<id>/', views.deleteowner, name='deleteowner'),
  path('barchart/', views.barchart, name='barchart'),
  path('piechart/', views.piechart, name='piechart'),
  path('datewisereport/', views.datewisereport, name='datewisereport'),
  path('datewisereport/excel/', views.datewisereport_excel, name='datewisereport_excel'),
  
]

