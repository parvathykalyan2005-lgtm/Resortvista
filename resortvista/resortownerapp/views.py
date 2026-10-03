import csv
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from adminapp.models import tbl_category, tbl_district, tbl_location
from resortownerapp.models import tbl_package, tbl_resort, tbl_packagedetails
from customerapp.models import tbl_booking
from guestapp.models import tbl_resortowner

# Create your views here.
def ownerindex(request):
    return render(request,'resortowner/ownerindex.html')
def resortadd(request):
    # Fetch categories and districts for the form
    categories = tbl_category.objects.all().order_by('category_name')
    districts = tbl_district.objects.all().order_by('district_name')

    if request.method == 'POST':
        resort_name = request.POST.get('resort_name')
        resort_address = request.POST.get('resort_address')
        resort_phone = request.POST.get('resort_phone')
        resort_image = request.FILES.get('resort_image')
        location_id = request.POST.get('location_id')
        category_id = request.POST.get('category_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        status = 'available'

        login_id = request.session.get('login_id')
        if not login_id:
            messages.error(request, 'Please login to add a resort.')
            return redirect('ownerindex')

        try:
            owner = tbl_resortowner.objects.get(login_id=login_id)
        except tbl_resortowner.DoesNotExist:
            messages.error(request, 'Owner profile not found.')
            return redirect('ownerindex')

        resort_obj = tbl_resort(
            resort_name=resort_name,
            resort_address=resort_address,
            resort_phone=resort_phone,
            resort_image=resort_image,
            location_id_id=location_id,
            category_id_id=category_id,
            amount=amount,
            description=description,
            status=status,
            owner_id_id=owner.owner_id,
        )
        resort_obj.save()
        messages.success(request, 'Resort Added Successfully')
        return redirect('ownerindex')

    return render(request, 'resortowner/resortadd.html', {
        'category': categories,
        'districts': districts,
    })

def owner_get_locations(request):
    district_id = request.GET.get('district_id')
    if district_id:
        try:
            # Try standard FK name; fallback to explicit _id in case of schema mismatch
            district_id_int = int(district_id)
            locations = tbl_location.objects.filter(district_id=district_id_int).values('location_id', 'location_name')
            if not locations:
                locations = tbl_location.objects.filter(district_id_id=district_id_int).values('location_id', 'location_name')
            return JsonResponse({'locations': list(locations)})
        except Exception as exc:
            return JsonResponse({'locations': [], 'error': str(exc)})
    return JsonResponse({'locations': []})
def viewresort(request):
    login_id = request.session.get('login_id')
    if not login_id:
        messages.error(request, 'Please login to view your resorts.')
        return redirect('ownerindex')

    try:
        owner = tbl_resortowner.objects.get(login_id=login_id)
    except tbl_resortowner.DoesNotExist:
        messages.error(request, 'Owner profile not found.')
        return redirect('ownerindex')
    # Categories for filter dropdown
    categories = tbl_category.objects.all().order_by('category_name')

    # Optional category filter via GET
    selected_category_id = request.GET.get('category_id')

    resorts_qs = tbl_resort.objects.filter(owner_id=owner.owner_id)
    if selected_category_id:
        try:
            resorts_qs = resorts_qs.filter(category_id=int(selected_category_id))
        except ValueError:
            pass

    resort_data = []
    for resort in resorts_qs.order_by('category_id'):
        # Read names directly from FK objects; avoid extra queries
        location_name = resort.location_id.location_name if resort.location_id else None
        category_name = resort.category_id.category_name if resort.category_id else None

        resort_data.append({
            'resort': resort,
            'location_name': location_name,
            'category_name': category_name,
        })

    return render(request, 'resortowner/viewresort.html', {
        'resorts': resort_data,
        'categories': categories,
        'selected_category_id': int(selected_category_id) if selected_category_id else None,
    })

def editresort(request, resort_id):
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        messages.error(request, 'Resort not found.')
        return redirect('viewresort')

    categories = tbl_category.objects.all().order_by('category_name')
    districts = tbl_district.objects.all().order_by('district_name')

    if request.method == 'POST':
        name = request.POST.get('resort_name')
        if name and name.strip():
            resort.resort_name = name.strip()

        address = request.POST.get('resort_address')
        if address and address.strip():
            resort.resort_address = address.strip()

        phone = request.POST.get('resort_phone')
        if phone and phone.strip():
            resort.resort_phone = phone.strip()

        if 'resort_image' in request.FILES:
            resort.resort_image = request.FILES['resort_image']

        location_id = request.POST.get('location_id')
        if location_id and str(location_id).strip():
            try:
                resort.location_id = int(location_id)
            except ValueError:
                pass

        category_id = request.POST.get('category_id')
        if category_id and str(category_id).strip():
            try:
                resort.category_id = int(category_id)
            except ValueError:
                pass

        amount = request.POST.get('amount')
        if amount and str(amount).strip():
            resort.amount = amount

        description = request.POST.get('description')
        if description is not None:
            resort.description = description

        resort.save()
        messages.success(request, 'Resort Updated Successfully')
        return redirect('viewresort')

    return render(request, 'resortowner/editresort.html', {
        'resort': resort,
        'categories': categories,
        'districts': districts,
    })

def deleteresort(request, resort_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    login_id = request.session.get('login_id')
    if not login_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        owner = tbl_resortowner.objects.get(login_id=login_id)
    except tbl_resortowner.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Owner profile not found'}, status=404)

    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Resort not found'}, status=404)

    if resort.owner_id_id != owner.owner_id:
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    resort.delete()
    return JsonResponse({'success': True})
def delete_resort(request, resort_id):
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
        resort.delete()
        messages.success(request, 'Resort Deleted Successfully')
    except tbl_resort.DoesNotExist:
        messages.error(request, 'Resort not found.')
    return redirect('viewresort')
def packageadd(request):
    # Limit resort options to the logged-in owner's resorts
    login_id = request.session.get('login_id')
    owner = None
    if login_id:
        try:
            owner = tbl_resortowner.objects.get(login_id=login_id)
        except tbl_resortowner.DoesNotExist:
            owner = None
    resorts = tbl_resort.objects.filter(owner_id=owner.owner_id) if owner else tbl_resort.objects.none()
    if request.method == 'POST':
        resort_id = request.POST.get('resort_id')
        package_name = request.POST.get('package_name')
        package_image = request.FILES.get('package_image')
        duration = request.POST.get('duration')
        # Multiple include items from dynamic form rows
        include_names = request.POST.getlist('include_name')
        include_amounts = request.POST.getlist('include_amount')
        max_people = request.POST.get('max_people')
        status = 'available'

        login_id = request.session.get('login_id')
        if not login_id:
            messages.error(request, 'Please login to add a package.')
            return redirect('ownerindex')

        try:
            owner = tbl_resortowner.objects.get(login_id=login_id)
        except tbl_resortowner.DoesNotExist:
            messages.error(request, 'Owner profile not found.')
            return redirect('ownerindex')

        # Compute grand total on the server (sum of include amounts only)
        from decimal import Decimal
        includes_total = Decimal('0')
        for amt in include_amounts:
            try:
                includes_total += Decimal(str(amt or '0'))
            except Exception:
                pass
        grand_total = includes_total

        # Safe resort FK assignment using ID
        try:
            resort_fk_id = int(resort_id) if resort_id else None
        except Exception:
            resort_fk_id = None

        if not resort_fk_id:
            messages.error(request, 'Please select a resort.')
            return redirect('packageadd')

        # Parse max_people to int if provided
        try:
            max_people_val = int(max_people) if max_people else None
        except Exception:
            max_people_val = None

        try:
            with transaction.atomic():
                package_obj = tbl_package(
                    resort_id_id=resort_fk_id,
                    package_name=package_name,
                    package_image=package_image,
                    duration=duration,
                    max_people=max_people_val,
                    status=status,
                    total_amount=grand_total,
                )
                package_obj.save()

                # Persist each include row into tbl_packagedetails
                primary_detail = None
                for name, amt in zip(include_names, include_amounts):
                    if name and name.strip():
                        try:
                            amt_dec = Decimal(str(amt or '0'))
                        except Exception:
                            amt_dec = Decimal('0')
                        detail = tbl_packagedetails.objects.create(
                            package_id=package_obj,
                            package_detail_name=name.strip(),
                            amount=amt_dec,
                        )
                        if primary_detail is None:
                            primary_detail = detail
                # Set the first detail as package.package_details_id if available
                # if primary_detail is not None:
                #     package_obj.package_details_id = primary_detail
                #     package_obj.save(update_fields=['package_details_id'])
        except Exception as e:
            messages.error(request, f'Failed to add package: {e}')
            return redirect('packageadd')
        messages.success(request, 'Package Added Successfully')
        return redirect('packageadd')
    return render(request,'resortowner/packageadd.html', {'resorts': resorts})
def packageview(request):
    # Restrict viewing to packages belonging to the logged-in owner's resorts
    login_id = request.session.get('login_id')
    if not login_id:
        messages.error(request, 'Please login to view your packages.')
        return redirect('ownerindex')

    try:
        owner = tbl_resortowner.objects.get(login_id=login_id)
    except tbl_resortowner.DoesNotExist:
        messages.error(request, 'Owner profile not found.')
        return redirect('ownerindex')

    packages = (
        tbl_package.objects
        .filter(resort_id__owner_id_id=owner.owner_id)
        .order_by('resort_id_id')
    )
    package_data = []
    from decimal import Decimal
    for package in packages:
        # Resolve resort name safely using FK id
        resort_name = None
        if package.resort_id_id:
            resort = tbl_resort.objects.filter(resort_id=package.resort_id_id).first()
            resort_name = resort.resort_name if resort else None

        # Gather include details and sum amounts
        details = list(tbl_packagedetails.objects.filter(package_id=package.package_id))
        includes_total = sum((d.amount or Decimal('0')) for d in details)

        package_data.append({
            'package': package,
            'resort_name': resort_name,
            'details': details,
            'includes_total': includes_total,
        })

    return render(request, 'resortowner/packageview.html', {'packages': package_data})

def packageedit(request, package_id):
    from decimal import Decimal
    try:
        package = tbl_package.objects.get(package_id=package_id)
    except tbl_package.DoesNotExist:
        messages.error(request, 'Package not found.')
        return redirect('packageview')

    resorts = tbl_resort.objects.all()

    if request.method == 'POST':
        package_name = request.POST.get('package_name')
        duration = request.POST.get('duration')
        max_people = request.POST.get('max_people')
        resort_id = request.POST.get('resort_id')
        include_names = request.POST.getlist('include_name')
        include_amounts = request.POST.getlist('include_amount')

        # Safe conversions
        try:
            max_people_val = int(max_people) if max_people else None
        except Exception:
            max_people_val = None
        try:
            resort_fk_id = int(resort_id) if resort_id else None
        except Exception:
            resort_fk_id = None

        # Recalculate grand total (sum of include amounts only)
        includes_total = Decimal('0')
        for amt in include_amounts:
            try:
                includes_total += Decimal(str(amt or '0'))
            except Exception:
                pass
        grand_total = includes_total

        # Update base package fields
        package.package_name = package_name
        package.duration = duration
        package.max_people = max_people_val
        if resort_fk_id:
            package.resort_id_id = resort_fk_id

        # Handle optional image update
        package_image = request.FILES.get('package_image')
        if package_image:
            package.package_image = package_image

        # Save base package first
        package.total_amount = grand_total
        package.save()

        # Replace includes: delete existing details and recreate from form
        tbl_packagedetails.objects.filter(package_id=package.package_id).delete()
        for name, amt in zip(include_names, include_amounts):
            if name and name.strip():
                try:
                    amt_dec = Decimal(str(amt or '0'))
                except Exception:
                    amt_dec = Decimal('0')
                tbl_packagedetails.objects.create(
                    package_id=package,
                    package_detail_name=name.strip(),
                    amount=amt_dec,
                )

        messages.success(request, 'Package updated successfully.')
        return redirect('packageview')

    # Derive resort_name and current details for display
    resort_name = None
    if package.resort_id_id:
        resort = tbl_resort.objects.filter(resort_id=package.resort_id_id).first()
        resort_name = resort.resort_name if resort else None

    details = tbl_packagedetails.objects.filter(package_id=package.package_id)

    return render(request, 'resortowner/packageedit.html', {
        'package': package,
        'resorts': resorts,
        'resort_name': resort_name,
        'details': details,
    })

def packagedelete(request, package_id):
    try:
        package = tbl_package.objects.get(package_id=package_id)
        package.delete()
        messages.success(request, 'Package deleted successfully.')
    except tbl_package.DoesNotExist:
        messages.error(request, 'Package not found.')
    return redirect('packageview')

def bookingreport(request):
    login_id = request.session.get('login_id')
    if not login_id:
        messages.error(request, 'Please login to view booking reports.')
        return redirect('ownerindex')

    try:
        owner = tbl_resortowner.objects.get(login_id=login_id)
    except tbl_resortowner.DoesNotExist:
        messages.error(request, 'Owner profile not found.')
        return redirect('ownerindex')

    booking_rows = []
    export_mode = (request.GET.get('export') or '').strip().lower()
    try:
        booking_list = (
            tbl_booking.objects
            .filter(resort_id__owner_id=owner, payment_id__payment_status='Paid')
            .order_by('-booking_id')
        )

        for booking in booking_list:
            resort_name = booking.resort_id.resort_name if booking.resort_id else 'N/A'
            package_name = booking.package_id.package_name if booking.package_id else None
            customer_name = booking.customer_id.customer_name if booking.customer_id else 'N/A'
            customer_phone = booking.customer_id.customer_phone if booking.customer_id else 'N/A'
            payment_status = booking.payment_id.payment_status if booking.payment_id else 'Pending'
            payment_amount = booking.payment_id.amount_paid if booking.payment_id else None
            payment_date = booking.payment_id.payment_date if booking.payment_id else None

            booking_rows.append({
                'booking': booking,
                'resort_name': resort_name,
                'package_name': package_name,
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'payment_status': payment_status,
                'payment_amount': payment_amount,
                'payment_date': payment_date,
            })
    except Exception:
        booking_rows = []

    if export_mode == 'excel':
        def _fmt_date(value):
            if not value:
                return ''
            try:
                return value.strftime('%Y-%m-%d')
            except Exception:
                return str(value)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="booking_report.csv"'
        writer = csv.writer(response)

        writer.writerow([
            'Booking ID',
            'Resort',
            'Customer',
            'Phone',
            'Check In',
            'Check Out',
            'Package',
            'Total Amount',
            'Paid Amount',
            'Payment Date',
            'Status',
        ])

        for item in booking_rows:
            writer.writerow([
                item['booking'].booking_id,
                item['resort_name'],
                item['customer_name'],
                item['customer_phone'],
                _fmt_date(item['booking'].check_in_date),
                _fmt_date(item['booking'].check_out_date),
                item['package_name'] or '-',
                item['booking'].total_amount or '0.00',
                item['payment_amount'] or '-',
                _fmt_date(item['payment_date']),
                item['payment_status'],
            ])

        return response

    return render(request, 'resortowner/bookingreport.html', {
        'bookings': booking_rows,
    })
def about(request):
    return render(request, 'resortowner/about.html')

