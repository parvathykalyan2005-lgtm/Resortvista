from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import os
import re

from .models import tbl_customer, tbl_login, tbl_resortowner
from adminapp.models import tbl_district, tbl_location
from django.http import HttpResponse

# Create your views here.
def index(request):
    return render(request,'guest/guestindex.html')

def resortownerreg(request):
    if request.method=='POST':
        owner_name=(request.POST.get('name') or '').strip()
        owner_email=(request.POST.get('email') or '').strip().lower()
        owner_phone=(request.POST.get('phone') or '').strip()
        licence_image=request.FILES.get('licence_image') or request.FILES.get('license_image')
        location_id=(request.POST.get('location_id') or '').strip()
        username=(request.POST.get('username') or '').strip()
        password=(request.POST.get('password') or '').strip()

        def _render_error(message):
            messages.error(request, message)
            districts = tbl_district.objects.all()
            return render(request, 'guest/resortownerreg.html', {'districts': districts})

        if not all([owner_name, owner_email, owner_phone, username, password, location_id]):
            return _render_error('All fields are required')

        if not re.fullmatch(r"[A-Za-z][A-Za-z\s]{1,49}", owner_name):
            return _render_error('Name should contain only letters and spaces (2-50 characters).')

        try:
            validate_email(owner_email)
        except ValidationError:
            return _render_error('Please enter a valid email address.')

        if not re.fullmatch(r"\+?[0-9]{10,15}", owner_phone):
            return _render_error('Phone number should contain 10 to 15 digits (optional + prefix).')

        if not re.fullmatch(r"[A-Za-z0-9_]{4,20}", username):
            return _render_error('Username should be 4-20 characters and can contain letters, numbers, and underscore only.')

        if not re.fullmatch(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#._-])[A-Za-z\d@$!%*?&#._-]{8,20}", password):
            return _render_error('Password must be 8-20 characters with uppercase, lowercase, number, and special character.')

        try:
            location_id_int = int(location_id)
        except (TypeError, ValueError):
            return _render_error('Please select a valid location.')

        if not tbl_location.objects.filter(location_id=location_id_int).exists():
            return _render_error('Please select a valid location.')

        if tbl_resortowner.objects.filter(owner_email=owner_email).exists():
            return _render_error('Email already registered')

        if tbl_login.objects.filter(username=username).exists():
            return _render_error('Username already taken')

        if licence_image:
            valid_content_types = {'image/jpeg', 'image/png', 'image/webp', 'image/jpg'}
            valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
            image_content_type = (getattr(licence_image, 'content_type', '') or '').lower()
            image_name = (getattr(licence_image, 'name', '') or '').lower()
            image_extension = os.path.splitext(image_name)[1]

            # Some browsers/upload sources send generic content-types.
            # Accept valid file extensions as a fallback for those cases.
            if image_content_type and image_content_type not in valid_content_types and image_extension not in valid_extensions:
                return _render_error('License image must be JPG, PNG, or WEBP format.')

            image_size = getattr(licence_image, 'size', 0) or 0
            if image_size <= 0:
                return _render_error('Please upload a valid license image file.')
            if image_size > 2 * 1024 * 1024:
                return _render_error('License image size must be 2MB or less.')

        resortowner_obj=tbl_resortowner()
        resortowner_obj.owner_name=owner_name
        resortowner_obj.owner_email=owner_email
        resortowner_obj.owner_phone=owner_phone
        resortowner_obj.licence_image=licence_image 
        resortowner_obj.location_id=location_id_int
        resortowner_obj.save()
        login_obj=tbl_login()
        login_obj.username=username
        login_obj.password=password
        login_obj.role='resortowner'
        login_obj.status='pending'
        login_obj.save()
        resortowner_obj.login_id_id=login_obj.login_id
        resortowner_obj.save()
        messages.success(request,'Resort Owner Registered Successfully')
        return redirect('resortownerreg')

    
    districts = tbl_district.objects.all()
    return render(request, 'guest/resortownerreg.html', {'districts': districts})

def ajax_get_locations(request):
    # Accept both 'district_id' and 'district' for compatibility
    raw_id = request.GET.get('district_id') or request.GET.get('district')
    if not raw_id:
        return JsonResponse({'locations': [], 'error': 'missing_param'})
    try:
        district_id_int = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({'locations': [], 'error': 'invalid_param'})

    # Use explicit FK id field for reliable filtering
    locations = tbl_location.objects.filter(district_id_id=district_id_int).values('location_id', 'location_name')
    return JsonResponse({'locations': list(locations)})
def login(request):
    return render(request,"guest/login.html")

def logout_view(request):
    # Clear session so all roles are logged out.
    request.session.flush()
    return redirect('login')

def login_process(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if tbl_login.objects.filter(username=username,password=password).exists():
            log = tbl_login.objects.get(username=username,password=password)
            request.session['login_id'] = log.login_id
            role=log.role
            if role =='admin':
                return redirect('/adminn/message/')
            elif role == 'resortowner':
                if log.status == 'Accepted':
                    return redirect('/resortowner/ownerindex/')
                else:
                   messages.error(request, "Not Verified Yet!")
                   return redirect('/login/')
            elif role =='customer':
                return redirect('/customer/customerindex/')

            else:
                messages.error(request, "Request not Accepted")
                return redirect('/login/')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('/login/')
    else:
        messages.error(request, "Invalid username or password")
        return redirect('/login/')
        #return HttpResponse("<script>alert('Invalid username or password...');window.location='/orphnagereg';</script>")
def customerreg(request):
    if request.method=='POST':
        customer_name=request.POST.get('name')
        customer_email=request.POST.get('email')
        customer_phone=request.POST.get('phone')
        location_id=request.POST.get('location_id')
        address=request.POST.get('address')
        username=request.POST.get('username')
        password=request.POST.get('password')

        if not all([customer_name, customer_email, customer_phone, location_id, address, username, password]):
            messages.error(request, 'All fields are required')
            return render(request, 'guest/customerreg.html')

        if tbl_login.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return render(request, 'guest/customerreg.html')
        customer_obj=tbl_customer()
        customer_obj.customer_name=customer_name
        customer_obj.customer_email=customer_email
        customer_obj.customer_phone=customer_phone
        customer_obj.location_id=location_id
        customer_obj.address=address
        customer_obj.save()

        login_obj=tbl_login()
        login_obj.username=username
        login_obj.password=password
        login_obj.role='customer'
        login_obj.status='Accepted'
        login_obj.save()
        customer_obj.login_id_id=login_obj.login_id
        customer_obj.save() 
        # Send welcome email (non-blocking failure)
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'parvathykk16@gmail.com'
            send_mail(
                subject='Welcome to ResortVista',
                message=(
                    f"Hi {customer_name},\n\n"
                    "Welcome to ResortVista! Your customer account has been created successfully.\n"
                    "You can now log in and explore resorts, packages, and bookings.\n\n"
                    "Thanks,\n"
                    "ResortVista Team"
                ),
                from_email=from_email,
                recipient_list=[customer_email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request,'Customer Registered Successfully')
        return redirect('login')
    districts = tbl_district.objects.all()
    return render(request, 'guest/customerreg.html', {'districts': districts})
def ajax_get_locations_customer(request):
    district_id = request.GET.get('district_id')
    if not district_id:
        return JsonResponse({'locations': [], 'error': 'missing_param'})
    try:
        district_id_int = int(district_id)
    except (TypeError, ValueError):
        return JsonResponse({'locations': [], 'error': 'invalid_param'})

    locations = tbl_location.objects.filter(district_id_id=district_id_int).values('location_id', 'location_name')
    return JsonResponse({'locations': list(locations)})
def choosereg(request):
    return render(request, 'guest/choosereg.html')
def about(request):
    return render(request,'guest/about.html')
def contact(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        subject = (request.POST.get('subject') or '').strip()
        message_text = (request.POST.get('message') or '').strip()

        if not all([name, email, phone, subject, message_text]):
            messages.error(request, 'Please fill all required fields before sending your message.')
            return redirect('guest_contact')

        if '@' not in email or '.' not in email:
            messages.error(request, 'Please enter a valid email address.')
            return redirect('guest_contact')

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

        return redirect('guest_contact')

    return render(request,'guest/contact.html')


