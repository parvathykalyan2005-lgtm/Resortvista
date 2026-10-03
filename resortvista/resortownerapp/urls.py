from django.urls import path
from . import views

urlpatterns = [
   path('ownerindex/', views.ownerindex, name='ownerindex'),
   path('resortadd/', views.resortadd, name='resortadd'),
   path('owner_get_locations/', views.owner_get_locations, name='owner_get_locations'),
   path('viewresort/', views.viewresort, name='viewresort'),
   path('editresort/<int:resort_id>/', views.editresort, name='editresort'),
   path('deleteresort/<int:resort_id>/', views.deleteresort, name='deleteresort'),
   path('packageadd/', views.packageadd, name='packageadd'),
   path('packageview/', views.packageview, name='packageview'),
   path('packageedit/<int:package_id>/', views.packageedit, name='packageedit'),
   path('packagedelete/<int:package_id>/', views.packagedelete, name='packagedelete'),
   path('bookingreport/', views.bookingreport, name='bookingreport'),
   path('about/', views.about, name='about'),
]