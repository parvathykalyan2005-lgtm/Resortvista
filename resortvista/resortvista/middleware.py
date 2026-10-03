from django.shortcuts import redirect

from guestapp.models import tbl_login


class RoleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ''

        role_by_prefix = {
            '/adminn/': 'admin',
            '/resortowner/': 'resortowner',
            '/customer/': 'customer',
        }

        required_role = None
        for prefix, role in role_by_prefix.items():
            if path.startswith(prefix):
                required_role = role
                break

        if required_role:
            login_id = request.session.get('login_id')
            if not login_id:
                return redirect('login')

            try:
                login_row = tbl_login.objects.get(login_id=login_id)
            except tbl_login.DoesNotExist:
                request.session.flush()
                return redirect('login')

            if login_row.role != required_role:
                request.session.flush()
                return redirect('login')

            if required_role == 'resortowner' and login_row.status != 'Accepted':
                request.session.flush()
                return redirect('login')

        response = self.get_response(request)
        return response
