from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from urllib.parse import urlencode
from adminapp.models import tbl_category, tbl_location
from resortownerapp.models import tbl_resort, tbl_package, tbl_packagedetails
from guestapp.models import tbl_customer
from .models import tbl_packagecustomizerequest, tbl_customizeitem, tbl_booking, tbl_payment
from datetime import datetime
from decimal import Decimal
# Create your views here.
def customerindex(request):
    # Check for payment success message from session
    payment_success = request.session.pop('payment_success', None)
    payment_error = request.session.pop('payment_error', None)
    paid_amount = request.session.pop('paid_amount', None)
    
    context = {
        'payment_success': payment_success,
        'payment_error': payment_error,
        'paid_amount': paid_amount,
    }
    return render(request, 'customer/index.html', context)
def resortview(request):
    # Prefer approved/public resorts; fallback to all if no status field match
    resorts_qs = tbl_resort.objects.all()
    # Optional category filter via GET
    selected_category_id = None
    selected_category_name = None
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            selected_category_id = int(category_id)
            resorts_qs = resorts_qs.filter(category_id=selected_category_id)
            try:
                selected_category_name = tbl_category.objects.get(category_id=selected_category_id).category_name
            except Exception:
                selected_category_name = None
        except Exception:
            selected_category_id = None
    try:
        approved_qs = resorts_qs.filter(status='approved')
        if approved_qs.exists():
            resorts_qs = approved_qs
    except Exception:
        pass

    resort_data = []
    for resort in resorts_qs.order_by('category_id'):
        # Resolve names via FK objects directly
        location_name = resort.location_id.location_name if resort.location_id else None
        category_name = resort.category_id.category_name if resort.category_id else None

        resort_data.append({
            'resort': resort,
            'location_name': location_name,
            'category_name': category_name,
        })

    # Categories for filter dropdown
    try:
        categories = tbl_category.objects.all().order_by('category_name')
    except Exception:
        categories = []

    return render(request, 'customer/resortview.html', {
        'resorts': resort_data,
        'categories': categories,
        'selected_category_id': selected_category_id,
        'selected_category_name': selected_category_name,
    })
def resortsingleview(request, resort_id):
    request.session['booking_type'] = 'direct'

    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        resort = None

    location_name = None
    category_name = None

    if resort:
        # Read from FK objects to avoid TypeError
        location_name = resort.location_id.location_name if resort.location_id else None
        category_name = resort.category_id.category_name if resort.category_id else None

    # Fetch available packages for the resort
    packages = []
    if resort:
        try:
            # Use proper FK filter and valid ordering field
            packages = (
                tbl_package.objects.filter(resort_id=resort, status='available')
                .order_by('total_amount')
            )
        except Exception:
            packages = []

    context = {
        'resort': resort,
        'location_name': location_name,
        'category_name': category_name,
        'packages': packages,
        'availability': None,
    }
    return render(request, 'customer/resortsingleview.html', context)

def check_availability(request, resort_id):
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        resort = None

    availability = {
        'checked': False,
        'status': 'available',   # 'available' or 'unavailable'
        'message': None,
    }

    # Reuse package listing for sidebar context
    packages = []
    if resort:
        try:
            packages = (
                tbl_package.objects.filter(resort_id=resort, status='available')
                .order_by('total_amount')
            )
        except Exception:
            packages = []

    if request.method == 'POST':
        date_in = request.POST.get('date_in')
        date_out = request.POST.get('date_out')

        if not date_in or not date_out:
            availability['checked'] = True
            availability['status'] = 'unavailable'
            availability['message'] = '❌ Please provide both Check In and Check Out dates.'
            availability['date_in'] = date_in
            availability['date_out'] = date_out
        else:
            availability['date_in'] = date_in
            availability['date_out'] = date_out
            try:
                d_in = datetime.strptime(date_in, '%Y-%m-%d').date()
                d_out = datetime.strptime(date_out, '%Y-%m-%d').date()
                today = datetime.today().date()
                
                if d_in < today:
                    availability['checked'] = True
                    availability['status'] = 'unavailable'
                    availability['message'] = '❌ Check In date cannot be in the past.'
                elif d_out <= d_in:
                    availability['checked'] = True
                    availability['status'] = 'unavailable'
                    availability['message'] = '❌ Check Out date must be after Check In date.'
                else:
                    # Check if there are any overlapping bookings for this resort
                    overlapping_bookings = tbl_booking.objects.filter(
                        resort_id=resort,
                        check_in_date__lt=d_out,
                        check_out_date__gt=d_in
                    )
                    
                    if overlapping_bookings.exists():
                        availability['checked'] = True
                        availability['status'] = 'unavailable'
                        availability['message'] = f'❌ Sorry, the resort is not available for the selected dates ({date_in} to {date_out}). It is already booked by another customer.'
                    else:
                        nights = (d_out - d_in).days
                        availability['checked'] = True
                        availability['status'] = 'available'
                        availability['message'] = f'✅ Great! The resort is available for {nights} night(s) from {date_in} to {date_out}.'
            except ValueError:
                availability['checked'] = True
                availability['status'] = 'unavailable'
                availability['message'] = '❌ Invalid date format. Please select valid dates.'

    context = {
        'resort': resort,
        'packages': packages,
        'location_name': resort.location_id.location_name if resort and resort.location_id else None,
        'category_name': resort.category_id.category_name if resort and resort.category_id else None,
        'availability': availability,
    }
    return render(request, 'customer/resortsingleview.html', context)

def check_availability_ajax(request, resort_id):
    """AJAX endpoint for real-time availability checking in booking page"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        return JsonResponse({'error': 'Resort not found'}, status=404)
    
    availability = {
        'checked': False,
        'status': 'available',
        'message': None,
    }
    
    date_in = request.POST.get('date_in')
    date_out = request.POST.get('date_out')
    
    if not date_in or not date_out:
        availability['checked'] = True
        availability['status'] = 'unavailable'
        availability['message'] = '❌ Please provide both Check In and Check Out dates.'
    else:
        try:
            d_in = datetime.strptime(date_in, '%Y-%m-%d').date()
            d_out = datetime.strptime(date_out, '%Y-%m-%d').date()
            today = datetime.today().date()
            
            if d_in < today:
                availability['checked'] = True
                availability['status'] = 'unavailable'
                availability['message'] = '❌ Check In date cannot be in the past.'
            elif d_out <= d_in:
                availability['checked'] = True
                availability['status'] = 'unavailable'
                availability['message'] = '❌ Check Out date must be after Check In date.'
            else:
                # Check if there are any overlapping bookings for this resort
                overlapping_bookings = tbl_booking.objects.filter(
                    resort_id=resort,
                    check_in_date__lt=d_out,
                    check_out_date__gt=d_in
                )
                
                if overlapping_bookings.exists():
                    availability['checked'] = True
                    availability['status'] = 'unavailable'
                    availability['message'] = f'❌ Sorry, this resort is not available for {date_in} to {date_out}. Already booked by another customer.'
                else:
                    nights = (d_out - d_in).days
                    availability['checked'] = True
                    availability['status'] = 'available'
                    availability['message'] = f'✅ Great! The resort is available for {nights} night(s) from {date_in} to {date_out}.'
        except ValueError:
            availability['checked'] = True
            availability['status'] = 'unavailable'
            availability['message'] = '❌ Invalid date format. Please select valid dates.'
    
    return JsonResponse(availability)

def booking(request, resort_id):
    
    # Prefill booking form with selected resort and optional dates
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        resort = None

    # Dates can arrive via GET (prefill) or POST (form submit)
    date_in = request.GET.get('date_in')
    date_out = request.GET.get('date_out')

    # Optional: show selected package and includes from customization step
    package = None
    package_id = request.GET.get('package_id')
    
    if package_id:
        try:
           
            request.session['package_id'] = package_id
            package = tbl_package.objects.get(package_id=int(package_id), resort_id=resort_id)
        except Exception:
            package = None


        
    # If form submitted: create booking(s) in tbl_booking
    if request.method == 'POST':
        post_date_in = request.POST.get('date_in') or date_in
        post_date_out = request.POST.get('date_out') or date_out

        # Resolve logged-in customer from session login_id, if available
        customer_obj = None
        login_id = request.session.get('login_id')
        if login_id:
            try:
                customer_obj = tbl_customer.objects.get(login_id_id=login_id)
            except Exception:
                customer_obj = None

        # Compute nights and base total for non-package bookings, if possible
        nights = None
        try:
            if post_date_in and post_date_out:
                d_in = datetime.strptime(post_date_in, '%Y-%m-%d').date()
                d_out = datetime.strptime(post_date_out, '%Y-%m-%d').date()
                if d_out > d_in:
                    nights = (d_out - d_in).days
        except Exception:
            nights = None

        # Try to pick up any customize requests from session for package bookings
        customize_ids = request.session.get('customize_request_ids') or []

        created = []
        if customize_ids:
            for cid in customize_ids:
                try:
                    req = tbl_packagecustomizerequest.objects.get(package_customize_id=cid)
                except tbl_packagecustomizerequest.DoesNotExist:
                    req = None
                if not req:
                    continue

                base_total = None
                try:
                    price_per_night = getattr(resort, 'amount', None)
                    if price_per_night is not None and nights:
                        base_total = Decimal(str(price_per_night)) * Decimal(str(nights))
                except Exception:
                    base_total = None

                try:
                    booking_row = tbl_booking.objects.create(
                        resort_id=resort if resort else None,
                        customer_id=customer_obj if customer_obj else None,
                        owner_id=resort.owner_id if resort and resort.owner_id else None,
                        package_id=req.package_id if req.package_id else None,
                        package_customize_id=req,
                        check_in_date=post_date_in or None,
                        check_out_date=post_date_out or None,
                        total_amount=(base_total if base_total is not None else (resort.amount if resort else None)),
                        booking_status='Booked',
                    )
                    created.append(booking_row.booking_id)
                except Exception:
                    pass
        else:
            # Normal booking (no package customization)
            total_amount = None
            try:
                price_per_night = getattr(resort, 'amount', None)
                if price_per_night is not None and nights:
                    total_amount = Decimal(str(price_per_night)) * Decimal(str(nights))
            except Exception:
                total_amount = None
            try:
                booking_row = tbl_booking.objects.create(
                    resort_id=resort if resort else None,
                    customer_id=customer_obj if customer_obj else None,
                    owner_id=resort.owner_id if resort and resort.owner_id else None,
                    package_id=package if package else None,
                    package_customize_id=None,
                    check_in_date=post_date_in or None,
                    check_out_date=post_date_out or None,
                    total_amount=(total_amount if total_amount is not None else (resort.amount if resort else None)),
                    booking_status='Booked',
                )
                created.append(booking_row.booking_id)
            except Exception:
                pass

        # Clear selection to avoid duplicate bookings on refresh
        try:
            request.session.pop('selected_includes', None)
            request.session.pop('customize_request_ids', None)
        except Exception:
            pass

        # Redirect to payment with context
        query = {
            'resort_id': resort_id,
            'date_in': post_date_in or '',
            'date_out': post_date_out or '',
        }
        return redirect(f"{reverse('payment')}?{urlencode(query)}")

    # Load available packages for this resort (for dynamic select)
    packages = []
    if resort:
        try:
            packages = (
                tbl_package.objects.filter(resort_id=resort, status='available')
                .order_by('total_amount')
            )
        except Exception:
            packages = []

    selected_includes = request.session.get('selected_includes')
    # Build multi-package summary when selected_includes is a dict of {package_id: [detail_ids]}
    multi_summary = None
    try:
        if isinstance(selected_includes, dict):
            items = []
            for pid_str, detail_ids in selected_includes.items():
                try:
                    pid = int(pid_str)
                except Exception:
                    continue
                try:
                    pkg_obj = tbl_package.objects.get(package_id=pid, resort_id=resort_id)
                except tbl_package.DoesNotExist:
                    continue
                details = []
                if detail_ids:
                    try:
                        details = list(
                            tbl_packagedetails.objects.filter(
                                package_id=pkg_obj,
                                package_details_id__in=detail_ids
                            )
                        )
                    except Exception:
                        details = []
                # Sum include amounts
                try:
                    includes_total = sum((d.amount or Decimal('0')) for d in details)
                except Exception:
                    includes_total = Decimal('0')
                # Grand total per package = resort price + includes total
                try:
                    base_price = getattr(resort, 'amount', None)
                    grand_total = (Decimal(str(base_price)) + includes_total).quantize(Decimal('0.01')) if base_price is not None else includes_total
                except Exception:
                    grand_total = includes_total
                items.append({'package': pkg_obj, 'details': details, 'includes_total': includes_total, 'grand_total': grand_total})
            multi_summary = items
    except Exception:
        multi_summary = None

    # Fallback: if no session-based summary, but package_ids are provided via GET, list packages.
    if not multi_summary:
        pkg_ids_str = (request.GET.get('package_ids') or '').strip()
        if pkg_ids_str:
            try:
                id_list = [int(x) for x in pkg_ids_str.split(',') if x.isdigit()]
            except Exception:
                id_list = []
            items = []
            for pid in id_list:
                try:
                    pkg_obj = tbl_package.objects.get(package_id=pid, resort_id=resort_id)
                except tbl_package.DoesNotExist:
                    continue
                # When details not specified, includes total is 0
                includes_total = Decimal('0')
                try:
                    base_price = getattr(resort, 'amount', None)
                    grand_total = (Decimal(str(base_price)) + includes_total).quantize(Decimal('0.01')) if base_price is not None else includes_total
                except Exception:
                    grand_total = includes_total
                items.append({'package': pkg_obj, 'details': [], 'includes_total': includes_total, 'grand_total': grand_total})
            if items:
                multi_summary = items
    # Single package_id via GET: build summary with includes
    if not multi_summary:
        single_pid = request.GET.get('package_id')
        request.session['package_id'] = single_pid
        if single_pid and str(single_pid).isdigit():
            try:
                pkg_obj = tbl_package.objects.get(package_id=int(single_pid), resort_id=resort_id)
                details = list(tbl_packagedetails.objects.filter(package_id=pkg_obj))
                try:
                    includes_total = sum((d.amount or Decimal('0')) for d in details)
                except Exception:
                    includes_total = Decimal('0')
                try:
                    base_price = getattr(resort, 'amount', None)
                    grand_total = (Decimal(str(base_price)) + includes_total).quantize(Decimal('0.01')) if base_price is not None else includes_total
                except Exception:
                    grand_total = includes_total
                multi_summary = [{'package': pkg_obj, 'details': details, 'includes_total': includes_total, 'grand_total': grand_total}]
            except Exception:
                multi_summary = None
    # Pull description from the latest customize request stored in session
    description = None
    try:
        customize_ids = request.session.get('customize_request_ids')
        if customize_ids:
            req = (
                tbl_packagecustomizerequest.objects
                .filter(package_customize_id__in=customize_ids)
                .order_by('-package_customize_id')
                .first()
            )
            if req:
                description = getattr(req, 'customize_description', None)
    except Exception:
        description = None

    # Overall grand total across all selected packages (if any)
    grand_total_all = None
    try:
        if multi_summary:
            # Sum all customization totals and add the resort base price only once
            includes_sum = Decimal('0')
            for it in multi_summary:
                inc = it.get('includes_total')
                if inc is not None:
                    try:
                        includes_sum += Decimal(str(inc))
                    except Exception:
                        pass
            base_price = getattr(resort, 'amount', None)
            if base_price is not None:
                grand_total_all = (Decimal(str(base_price)) + includes_sum).quantize(Decimal('0.01'))
            else:
                grand_total_all = includes_sum.quantize(Decimal('0.01'))
    except Exception:
        grand_total_all = None

    context = {
        'resort': resort,
        'package': package,
        'packages': packages,
        'date_in': date_in,
        'date_out': date_out,
        'selected_includes': selected_includes,
        'multi_summary': multi_summary,
        'description': description,
        'grand_total_all': grand_total_all,
    }
    return render(request, 'customer/booking.html', context)

def customize_packages(request, resort_id):
    
    # Load resort
    try:
        resort = tbl_resort.objects.get(resort_id=resort_id)
    except tbl_resort.DoesNotExist:
        resort = None

    date_in = request.GET.get('date_in') or request.POST.get('date_in')
    date_out = request.GET.get('date_out') or request.POST.get('date_out')

    if request.method == 'POST':
        # Save selections and redirect to booking
        selected_includes = {}
        customize_request_ids = []
        customer_obj = None
        login_id = request.session.get('login_id')
        if login_id:
            try:
                customer_obj = tbl_customer.objects.get(login_id_id=login_id)
            except Exception:
                customer_obj = None

        # Get all package IDs that were submitted
        package_ids_list = request.POST.getlist('package_ids[]')
        
        # Process each submitted package
        for pkg_id_str in package_ids_list:
            try:
                pkg_id = int(pkg_id_str)
            except (ValueError, TypeError):
                continue
                
            try:
                pkg = tbl_package.objects.get(package_id=pkg_id, resort_id=resort_id)
                m=pkg.package_id
                request.session['Cpackage_id']=int(m)
                request.session['booking_type'] = 'customized'


            except tbl_package.DoesNotExist:
                continue
            
            # Get includes for this package
            includes = request.POST.getlist(f'includes[{pkg_id}]')
            
            # Convert includes to integers
            includes_int = []
            for inc in includes:
                try:
                    includes_int.append(int(inc))
                except (ValueError, TypeError):
                    continue
            
            # Calculate includes total from selected package details
            includes_total = Decimal('0.00')
            detail_objects = []
            
            if includes_int:
                detail_objects = list(tbl_packagedetails.objects.filter(
                    package_id=pkg,
                    package_details_id__in=includes_int
                ))
                for d in detail_objects:
                    if d.amount:
                        includes_total += Decimal(str(d.amount))
            
            # Use only the cus
            # tomized includes total as the grand total
            grand_total = includes_total
            
            # Ensure grand_total is properly formatted
            grand_total = grand_total.quantize(Decimal('0.01'))
            
            # Create customize request for this package with calculated grand total
            req = tbl_packagecustomizerequest.objects.create(
                package_id=pkg,
                customer_id=customer_obj,
                total_amount=grand_total,
            )
            customize_request_ids.append(req.package_customize_id)
            
            # Store selected includes for session
            selected_includes[str(pkg_id)] = includes_int
            
            # Create customize items for selected package details
            for d in detail_objects:
                tbl_customizeitem.objects.get_or_create(
                    package_customize_id=req,
                    package_details_id=d,
                    defaults={'status': 'Added'}
                )

        request.session['selected_includes'] = selected_includes
        request.session['customize_request_ids'] = customize_request_ids

        query = {'date_in': date_in or '', 'date_out': date_out or ''}
        return redirect(f"{reverse('booking', args=[resort_id])}?{urlencode(query)}")

    # GET: build selected packages from query params
    ids = (request.GET.get('package_ids') or '').strip()
    qtys = (request.GET.get('quantities') or '').strip()
    id_list = [int(x) for x in ids.split(',') if x.isdigit()]
    qty_list = [int(x) for x in qtys.split(',') if x.isdigit()]

    selected_packages = []
    for idx, pkg_id in enumerate(id_list):
        try:
            pkg = tbl_package.objects.get(package_id=pkg_id, resort_id=resort_id)
        except tbl_package.DoesNotExist:
            continue
        includes_list = list(tbl_packagedetails.objects.filter(package_id=pkg))
        qty = qty_list[idx] if idx < len(qty_list) and qty_list[idx] > 0 else 1
        selected_packages.append({
            'package': pkg,
            'qty': qty,
            'includes_list': includes_list,
        })

    return render(request, 'customer/multipackagecustomize.html', {
        'resort': resort,
        'selected_packages': selected_packages,
        'package_ids': ids,
        'quantities': qtys,
        'date_in': date_in,
        'date_out': date_out,
    })
def payment(request):
    c_t = None
    package_id1 = request.session.get('Cpackage_id')
    booking_type = request.session.get('booking_type') 
    total_customized = Decimal('0.00')
    customer_obj = None

    if package_id1:
        if booking_type == 'customized':
            c_t = tbl_packagecustomizerequest.objects.filter(
                package_id=package_id1
            ).order_by('-package_customize_id').first()
            
            if c_t and c_t.total_amount:
                total_customized = Decimal(str(c_t.total_amount))
        
        else:
            total_customized = Decimal('0.00')
    
       
        

    # Optional context: resort, dates, and selected packages summary
    resort = None
    date_in = request.GET.get('date_in')
    date_out = request.GET.get('date_out')
    resort_id_param = request.GET.get('resort_id')
   
    if resort_id_param and resort_id_param.isdigit():
        try:
            resort = tbl_resort.objects.get(resort_id=int(resort_id_param))
        except tbl_resort.DoesNotExist:
            resort = None

    # Resolve logged-in customer for both GET context and POST fallback
    login_id = request.session.get('login_id')
    if login_id:
        try:
            customer_obj = tbl_customer.objects.get(login_id_id=login_id)
            request.session['customer_id'] = customer_obj.customer_id
        except Exception:
            customer_obj = None

    if not customer_obj:
        session_customer_id = request.session.get('customer_id')
        if session_customer_id and str(session_customer_id).isdigit():
            try:
                customer_obj = tbl_customer.objects.get(customer_id=int(session_customer_id))
            except Exception:
                customer_obj = None

   
    if request.method == 'POST':
        posted_customer_id = request.POST.get('customer_id')

        # Find the most recent booking for this customer/resort/dates
        booking_obj = None
        try:
            qs = tbl_booking.objects.all()
            if customer_obj:
                qs = qs.filter(customer_id=customer_obj)
            if resort:
                qs = qs.filter(resort_id=resort)
            if date_in:
                qs = qs.filter(check_in_date=date_in)
            if date_out:
                qs = qs.filter(check_out_date=date_out)
            booking_obj = qs.order_by('-booking_id').first()
        except Exception:
            booking_obj = None

        # Fallbacks to ensure payment.customer_id is set when possible
        if not customer_obj and posted_customer_id and str(posted_customer_id).isdigit():
            try:
                customer_obj = tbl_customer.objects.get(customer_id=int(posted_customer_id))
            except Exception:
                customer_obj = None
        if not customer_obj and booking_obj and booking_obj.customer_id:
            customer_obj = booking_obj.customer_id

        resolved_customer_id = None
        if customer_obj and getattr(customer_obj, 'customer_id', None):
            resolved_customer_id = customer_obj.customer_id
        elif posted_customer_id and str(posted_customer_id).isdigit():
            resolved_customer_id = int(posted_customer_id)
        elif booking_obj and booking_obj.customer_id:
            resolved_customer_id = booking_obj.customer_id.customer_id

        if resolved_customer_id:
            request.session['customer_id'] = resolved_customer_id

        # Determine base room amount
        base_amount = Decimal('0.00')
        if booking_obj and getattr(booking_obj, 'total_amount', None) is not None:
            base_amount = Decimal(str(booking_obj.total_amount))
        else:
        #     # Fallback: compute room total from resort price and nights
            if resort and getattr(resort, 'amount', None) is not None and date_in and date_out:
                try:
                    d_in = datetime.strptime(date_in, '%Y-%m-%d').date()
                    d_out = datetime.strptime(date_out, '%Y-%m-%d').date()
                    if d_out > d_in:
                        nights = (d_out - d_in).days
                        base_amount = (Decimal(str(resort.amount)) * Decimal(str(nights))).quantize(Decimal('0.01'))
                except Exception:
                    pass
        
      
        amount_paid = base_amount + total_customized

        # Persist payment
        payment_obj = None
        try:
            payment_obj = tbl_payment.objects.create(
                booking_id=booking_obj if booking_obj else None,
                payment_date=datetime.today().date(),
                amount_paid=amount_paid,
                payment_status='Paid',
                customer_id_id=resolved_customer_id,
            )
            payment_success = True
            
            # Update booking with payment_id and full total amount
            if booking_obj:
                try:
                    booking_obj.payment_id = payment_obj
                    booking_obj.total_amount = amount_paid
                    booking_obj.save()
                except Exception:
                    pass
        except Exception:
            payment_success = False

        # Optionally clear session selections post payment
        try:
            request.session.pop('selected_includes', None)
            request.session.pop('customize_request_ids', None)
        except Exception:
            pass

        # Store success message in session and redirect to customerindex
        if payment_success:
            request.session['payment_success'] = True
            request.session['paid_amount'] = str(amount_paid) if amount_paid else None
        else:
            request.session['payment_error'] = True
        
        return redirect('customerindex')

    # GET: build optional selected packages summary from session
    selected_includes = request.session.get('selected_includes')
    customize_request_ids = request.session.get('customize_request_ids') or []
    
    multi_summary = None
    customized_amounts = {}
    
    # # Fetch customized amounts from tbl_packagecustomizerequest
    if customize_request_ids:
        try:
            customize_requests = tbl_packagecustomizerequest.objects.filter(
                package_customize_id__in=customize_request_ids
            )
            for req in customize_requests:
                if req.package_id:
                    customized_amounts[req.package_id.package_id] = req.total_amount
        except Exception:
            pass
    
    try:
        if isinstance(selected_includes, dict):
            items = []
            for pid_str, detail_ids in selected_includes.items():
                try:
                    pid = int(pid_str)
                except Exception:
                    continue
                try:
                    pkg_obj = tbl_package.objects.get(package_id=pid)
                except tbl_package.DoesNotExist:
                    continue
                details = []
                if detail_ids:
                    try:
                        details = list(
                            tbl_packagedetails.objects.filter(
                                package_id=pkg_obj,
                                package_details_id__in=detail_ids
                            )
                        )
                    except Exception:
                        details = []
                
                # Add customized amount for this package
                customized_amt = customized_amounts.get(pid, Decimal('0.00'))
                items.append({
                    'package': pkg_obj, 
                    'details': details,
                    'customized_amount': customized_amt
                })
            multi_summary = items
    except Exception:
        multi_summary = None

    # # Fallback: if no session summary, load the latest booking's package (if present)
    if not multi_summary:
        booking_obj = None
        customer_obj = None
        login_id = request.session.get('login_id')
        if login_id:
            try:
                customer_obj = tbl_customer.objects.get(login_id_id=login_id)
            except Exception:
                customer_obj = None
        try:
            qs = tbl_booking.objects.all()
            if customer_obj:
                qs = qs.filter(customer_id=customer_obj)
            if resort:
                qs = qs.filter(resort_id=resort)
            if date_in:
                qs = qs.filter(check_in_date=date_in)
            if date_out:
                qs = qs.filter(check_out_date=date_out)
            
            booking_obj = qs.order_by('-booking_id').first()
        except Exception:
            booking_obj = None

        if booking_obj and getattr(booking_obj, 'package_id', None):
            try:
                pkg_obj = booking_obj.package_id
                details = list(tbl_packagedetails.objects.filter(package_id=pkg_obj))
                c_t=tbl_packagecustomizerequest.objects.filter(package_id=package_id1).last()

                multi_summary = [{'package': pkg_obj, 'details': details,'total_customized': c_t}]
            except Exception:
                pass
            
    return render(request, 'customer/payment.html', {
        'resort': resort,          
        'date_in': date_in,
        'date_out': date_out,
        'multi_summary': multi_summary,
        'total_customized': total_customized,
        'customer_id': customer_obj.customer_id if customer_obj else '',
                

    })

def mybookings(request):
    # Get logged-in customer
    customer_obj = None
    login_id = request.session.get('login_id')
    if login_id:
        try:
            customer_obj = tbl_customer.objects.get(login_id_id=login_id)
        except Exception:
            customer_obj = None
    
    # Fetch only paid bookings for this customer
    bookings = []
    if customer_obj:
        try:
            # Filter bookings that have a payment with 'Paid' status
            booking_list = tbl_booking.objects.filter(
                customer_id=customer_obj,
                payment_id__payment_status='Paid'
            ).order_by('-booking_id')
            
            for booking in booking_list:
                # Get payment status and amount
                payment_status = 'Paid'
                payment_amount = None
                if booking.payment_id:
                    payment_status = booking.payment_id.payment_status
                    payment_amount = booking.payment_id.amount_paid
                
                # Get package details if available
                package_name = None
                if booking.package_id:
                    package_name = booking.package_id.package_name
                
                bookings.append({
                    'booking': booking,
                    'resort_name': booking.resort_id.resort_name if booking.resort_id else 'N/A',
                    'location': booking.resort_id.location_id.location_name if booking.resort_id and booking.resort_id.location_id else 'N/A',
                    'package_name': package_name,
                    'payment_status': payment_status,
                    'payment_amount': payment_amount,
                })
        except Exception:
            bookings = []
    
    return render(request, 'customer/mybooking.html', {
        'bookings': bookings,
    })
def aboutc(request):
    return render(request, 'customer/aboutc.html')


def contactc(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        subject = (request.POST.get('subject') or '').strip()
        message_text = (request.POST.get('message') or '').strip()

        if not all([name, email, phone, subject, message_text]):
            messages.error(request, 'Please fill all required fields before sending your message.')
            return redirect('contactc')

        if '@' not in email or '.' not in email:
            messages.error(request, 'Please enter a valid email address.')
            return redirect('contactc')

        support_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'support@resortvista.com'

        try:
            send_mail(
                subject=f"[ResortVista Contact] {subject}",
                message=(
                    f"Name: {name}\n"
                    f"Email: {email}\n"
                    f"Phone: {phone}\n\n"
                    f"Message:\n{message_text}"
                ),
                from_email=support_email,
                recipient_list=[support_email],
                fail_silently=True,
            )
            messages.success(request, 'Thank you for contacting ResortVista. Our team will reach out to you shortly.')
        except Exception:
            messages.error(request, 'Your message could not be sent at the moment. Please try again later.')

        return redirect('contactc')

    return render(request, 'customer/contact.html')