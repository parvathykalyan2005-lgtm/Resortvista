from guestapp.models import tbl_customer


def customer_header_context(request):
    if not (request.path or '').startswith('/customer/'):
        return {}

    login_id = request.session.get('login_id')
    if not login_id:
        return {'customer_display_name': ''}

    customer_name = (
        tbl_customer.objects
        .filter(login_id_id=login_id)
        .values_list('customer_name', flat=True)
        .first()
    )

    return {'customer_display_name': (customer_name or '').strip()}
