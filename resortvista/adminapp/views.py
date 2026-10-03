from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from django.conf import settings
from django.core.mail import send_mail
from datetime import datetime
import csv
import re
from guestapp.models import tbl_login, tbl_resortowner, tbl_customer
from customerapp.models import tbl_booking
from resortownerapp.models import tbl_resort
from .models import tbl_category, tbl_district, tbl_location

# Create your views here.
NAME_VALIDATION_PATTERN = re.compile(r'^[A-Z][A-Za-z ]*$')


def _has_capitalized_first_letter(value):
    cleaned_value = (value or '').strip()
    return bool(cleaned_value and NAME_VALIDATION_PATTERN.fullmatch(cleaned_value))


def message(request):
    # Aggregate bookings by resort for the dashboard bar chart.
    chart_rows = (
        tbl_booking.objects.values('resort_id__resort_name')
        .annotate(total=Count('booking_id'))
        .order_by('-total', 'resort_id__resort_name')
    )
    labels = [row['resort_id__resort_name'] or 'Unknown' for row in chart_rows]
    data = [row['total'] for row in chart_rows]

    # Aggregate bookings by category for the pie chart.
    pie_rows = (
        tbl_booking.objects.values('resort_id__category_id__category_name')
        .annotate(total=Count('booking_id'))
        .order_by('-total', 'resort_id__category_id__category_name')
    )
    pie_labels = [row['resort_id__category_id__category_name'] or 'Unknown' for row in pie_rows]
    pie_data = [row['total'] for row in pie_rows]

    top_resort_name = labels[0] if labels else 'N/A'
    top_resort_bookings = data[0] if data else 0
    top_category_name = pie_labels[0] if pie_labels else 'N/A'
    top_category_bookings = pie_data[0] if pie_data else 0

    context = {
        'labels': labels,
        'data': data,
        'pie_labels': pie_labels,
        'pie_data': pie_data,
        'total_bookings': tbl_booking.objects.count(),
        'total_customers': tbl_customer.objects.count(),
        'total_resorts': tbl_resort.objects.count(),
        'total_categories': tbl_category.objects.count(),
        'top_resort_name': top_resort_name,
        'top_resort_bookings': top_resort_bookings,
        'top_category_name': top_category_name,
        'top_category_bookings': top_category_bookings,
    }
    return render(request, 'admin/index1.html', context)


def profile(request):
    login_id = request.session.get('login_id')
    if not login_id:
        return redirect('login')

    try:
        admin_login = tbl_login.objects.get(login_id=login_id, role='admin')
    except tbl_login.DoesNotExist:
        request.session.flush()
        return redirect('login')

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()

        if action == 'update_username':
            new_username = (request.POST.get('username') or '').strip()

            if not new_username:
                messages.error(request, 'Username is required.')
            elif not re.fullmatch(r"[A-Za-z0-9_]{4,20}", new_username):
                messages.error(request, 'Username must be 4-20 characters and contain only letters, numbers, and underscore.')
            elif tbl_login.objects.filter(username=new_username).exclude(login_id=admin_login.login_id).exists():
                messages.error(request, 'Username is already taken. Please choose another one.')
            else:
                admin_login.username = new_username
                admin_login.save(update_fields=['username'])
                messages.success(request, 'Username updated successfully.')

        elif action == 'change_password':
            current_password = (request.POST.get('current_password') or '').strip()
            new_password = (request.POST.get('new_password') or '').strip()
            confirm_password = (request.POST.get('confirm_password') or '').strip()

            if not current_password or not new_password or not confirm_password:
                messages.error(request, 'All password fields are required.')
            elif current_password != admin_login.password:
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New password and confirm password do not match.')
            elif current_password == new_password:
                messages.error(request, 'New password must be different from current password.')
            elif not re.fullmatch(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#._-])[A-Za-z\d@$!%*?&#._-]{8,20}", new_password):
                messages.error(request, 'Password must be 8-20 characters with uppercase, lowercase, number, and special character.')
            else:
                admin_login.password = new_password
                admin_login.save(update_fields=['password'])
                messages.success(request, 'Password changed successfully.')

        else:
            messages.error(request, 'Invalid profile action.')

        return redirect('admin_profile')

    return render(request, 'admin/profile.html', {'admin_login': admin_login})


def districtreg(request):
    if request.method == 'POST':
        district_name = (request.POST.get('district_name') or '').strip()
        if not _has_capitalized_first_letter(district_name):
            messages.error(request, 'District name must start with a capital letter and contain only letters and spaces.')
            return render(request, 'admin/district.html')
        district_obj= tbl_district()
        district_obj.district_name=district_name
        district_obj.save()
        messages.success(request, 'District successfully inserted')
        return redirect('districtreg')
    return render(request, 'admin/district.html')
def viewdistrict(request):
    district_data = tbl_district.objects.all()
    return render(request, 'admin/viewdistrict.html', {'district': district_data})
def deletedistrict(request, id):
    district_obj = tbl_district.objects.get(district_id=id)
    district_obj.delete()
    return viewdistrict(request)
def editdistrict(request, id):
    district_obj = tbl_district.objects.get(district_id=id)
    if request.method == 'POST':
        district_name = request.POST.get('district_name')
        district_obj.district_name = district_name
        district_obj.save()
        return viewdistrict(request)
    return render(request, 'admin/editdistrict.html', {'district': district_obj})
def locationreg(request):
    district_data = tbl_district.objects.all()
    if request.method == 'POST':
        district_id = request.POST.get('district_id')
        location_name = (request.POST.get('location_name') or '').strip()
        if not _has_capitalized_first_letter(location_name):
            messages.error(request, 'Location name must start with a capital letter and contain only letters and spaces.')
            return render(request, 'admin/location.html', {'district': district_data})
        # Correct lookup: tbl_district uses primary key field 'district_id'
        district_obj = tbl_district.objects.get(district_id=district_id)
        location_obj = tbl_location()
        location_obj.district_id = district_obj
        location_obj.location_name = location_name
        location_obj.save()
        messages.success(request, 'Successfully inserted')
        return redirect('locationreg')
    return render(request, 'admin/location.html', {'district': district_data})
def locationview(request):
    selected = request.GET.get('district')
    district_data = tbl_district.objects.all()
    if selected and str(selected).isdigit():
        # Filter by the raw FK id column when field is named 'district_id'
        location_data = tbl_location.objects.filter(district_id_id=int(selected))
        selected_district_int = int(selected)
        selected_district = str(selected)
    else:
        # Show nothing until a district is selected
        location_data = []
        selected_district_int = None
        selected_district = ''
    return render(
        request,
        'admin/locationview.html',
        {
            'location': location_data,
            'district': district_data,
            'selected_district_int': selected_district_int,
            'selected_district': selected_district,
        },
    )
def admin_get_locations(request):
    # AJAX endpoint: return locations JSON filtered by district query param
    district = request.GET.get('district')
    if not district:
        return JsonResponse({'locations': []})
    try:
        district_id = int(district)
    except ValueError:
        return JsonResponse({'locations': []})

    # Filter using explicit fk column name if standard filter didn't work for user
    # Generally filter(district_id=district_id) works if district_id is not shadowing FK descriptor,
    # but filter(district_id_id=district_id) is always safe for raw IDs.
    locs = list(tbl_location.objects.filter(district_id_id=district_id).values('location_id', 'location_name'))
    
    return JsonResponse({'locations': locs})

def editcategory(request, id):
    category_obj = tbl_category.objects.get(category_id=id)
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        category_image = request.FILES.get('category_image')
        category_obj.category_name = category_name
        if category_image:  # Only update if new image provided
            category_obj.category_image = category_image
        category_obj.save()
        return viewcategory(request)
    return render(request, 'admin/editcategory.html', {'category': category_obj})

def deletecategory(request, id):
    category_obj = tbl_category.objects.get(category_id=id)
    category_obj.delete()
    return viewcategory(request)

def categoryreg(request):
    if request.method == "POST":
        category_name = (request.POST.get("category_name") or '').strip()
        category_image = request.FILES.get("category_image")
        
        if not category_name or not category_image:
            messages.error(request, 'Category name and image are required.')
            return render(request, "admin/category.html")
        if not _has_capitalized_first_letter(category_name):
            messages.error(request, 'Category name must start with a capital letter and contain only letters and spaces.')
            return render(request, "admin/category.html")
        
        category_obj = tbl_category()
        category_obj.category_name = category_name
        category_obj.category_image = category_image
        category_obj.save()
        return viewcategory(request)  # Redirect to view instead of external URL
    return render(request, "admin/category.html")
def viewcategory(request):
    category_data = tbl_category.objects.all()
    return render(request, 'admin/viewcategory.html', {'category': category_data})

def editlocation(request, id):
    location_obj = tbl_location.objects.get(location_id=id)
    district_data = tbl_district.objects.all()
    if request.method == 'POST':
        location_name = request.POST.get('location_name')
        district_id = request.POST.get('district_id')
        district_obj = tbl_district.objects.get(district_id=district_id)
        location_obj.location_name = location_name
        # Assign FK correctly; field is named 'district_id'
        location_obj.district_id = district_obj
        location_obj.save()
        return locationview(request)
    return render(request, 'admin/editlocation.html', {'location': location_obj, 'district': district_data})

def deletelocation(request, id):
    location_obj = tbl_location.objects.get(location_id=id)
    location_obj.delete()
    return locationview(request)
def ownerverify(request):
    resortowner_data = tbl_resortowner.objects.all()
    return render(request, 'admin/ownerverify.html', {'resortowner': resortowner_data})
def acceptowner(request, id):
    try:
        resortowner_obj = tbl_resortowner.objects.get(owner_id=id)
        login_obj = tbl_login.objects.get(login_id=resortowner_obj.login_id_id)
        login_obj.status = 'Accepted'
        login_obj.save()
        # Notify owner via email (non-blocking failure)
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'parvathykk16@gmail.com'
            send_mail(
                subject='Resort Owner Account Approved',
                message=(
                    f"Hi {resortowner_obj.owner_name},\n\n"
                    "Your resort owner account has been approved. You can now log in and manage your resorts.\n\n"
                    "Thanks,\n"
                    "ResortVista Team"
                ),
                from_email=from_email,
                recipient_list=[resortowner_obj.owner_email],
                fail_silently=True,
            )
        except Exception:
            pass
        messages.success(request, 'Owner accepted successfully.')
    except tbl_resortowner.DoesNotExist:
        messages.error(request, 'Owner not found.')
    except tbl_login.DoesNotExist:
        messages.error(request, 'Login record not found for this owner.')
    return redirect('ownerverify')
def deleteowner(request, id):
    try:
        resortowner_obj = tbl_resortowner.objects.get(owner_id=id)
        # Attempt to load associated login; it may not exist
        try:
            login_obj = tbl_login.objects.get(login_id=resortowner_obj.login_id_id)
        except tbl_login.DoesNotExist:
            login_obj = None
        resortowner_obj.delete()
        if login_obj:
            login_obj.delete()
        messages.success(request, 'Owner rejected and removed.')
    except tbl_resortowner.DoesNotExist:
        messages.error(request, 'Owner not found.')
    return redirect('ownerverify') 
def barchart(request):
    # Aggregate bookings by resort for the bar chart.
    chart_rows = (
        tbl_booking.objects.values('resort_id__resort_name')
        .annotate(total=Count('booking_id'))
        .order_by('-total', 'resort_id__resort_name')
    )
    labels = [row['resort_id__resort_name'] or 'Unknown' for row in chart_rows]
    data = [row['total'] for row in chart_rows]
    context = {
        'labels': labels,
        'data': data,
    }
    return render(request, 'admin/barchart.html', context)
def piechart(request):
    # Aggregate bookings by category for the pie chart.
    chart_rows = (
        tbl_booking.objects.values('resort_id__category_id__category_name')
        .annotate(total=Count('booking_id'))
        .order_by('-total', 'resort_id__category_id__category_name')
    )
    labels = [row['resort_id__category_id__category_name'] or 'Unknown' for row in chart_rows]
    data = [row['total'] for row in chart_rows]
    context = {
        'labels': labels,
        'data': data,
    }
    return render(request, 'admin/piechart.html', context)


def _parse_date(date_value):
    if not date_value:
        return None
    try:
        return datetime.strptime(date_value, '%Y-%m-%d').date()
    except ValueError:
        return None


def datewisereport(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    from_date_obj = _parse_date(from_date)
    to_date_obj = _parse_date(to_date)

    bookings = tbl_booking.objects.select_related('resort_id', 'customer_id').order_by('-booking_id')

    if from_date_obj and to_date_obj:
        bookings = bookings.filter(check_in_date__range=[from_date_obj, to_date_obj])
    elif from_date_obj:
        bookings = bookings.filter(check_in_date__gte=from_date_obj)
    elif to_date_obj:
        bookings = bookings.filter(check_in_date__lte=to_date_obj)

    return render(
        request,
        'admin/datewisereport.html',
        {
            'bookings': bookings,
            'from_date': from_date,
            'to_date': to_date,
        },
    )


def datewisereport_excel(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    from_date_obj = _parse_date(from_date)
    to_date_obj = _parse_date(to_date)

    bookings = tbl_booking.objects.select_related('resort_id', 'customer_id').order_by('-booking_id')

    if from_date_obj and to_date_obj:
        bookings = bookings.filter(check_in_date__range=[from_date_obj, to_date_obj])
    elif from_date_obj:
        bookings = bookings.filter(check_in_date__gte=from_date_obj)
    elif to_date_obj:
        bookings = bookings.filter(check_in_date__lte=to_date_obj)

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="datewise_booking_report.xls"'

    writer = csv.writer(response, delimiter='\t')
    writer.writerow([
        'Booking ID',
        'Customer Name',
        'Resort Name',
        'Check In Date',
        'Check Out Date',
        'Total Amount',
        'Booking Status',
    ])

    for booking in bookings:
        writer.writerow([
            booking.booking_id,
            booking.customer_id.customer_name if booking.customer_id else '',
            booking.resort_id.resort_name if booking.resort_id else '',
            booking.check_in_date,
            booking.check_out_date,
            booking.total_amount,
            booking.booking_status,
        ])

    return response


