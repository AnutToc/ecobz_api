from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.core.cache import cache
from api.models import *
from api.utils.logger import log_exception, log_action, log_warning

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import os, requests 
from datetime import datetime, timedelta

from dotenv import load_dotenv
import warnings
import sys

load_dotenv()
warnings.filterwarnings("ignore")
print(sys.version)

ODOO_DB = os.getenv('ODOO_DB')

import logging

odoo_logger = logging.getLogger('odoo')

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING)
        }
    )
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def odoo_login(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        log_action("odoo_login", "start", user_id=username)
        db = os.getenv('ODOO_DB')

        if not username or not password:
            log_warning("odoo_login", "missing credentials", user_id=username)
            odoo_logger.warning(f"Login failed: Missing credentials - username={username}")
            return Response({'success': False, 'message': 'กรุณาระบุชื่อผู้ใช้และรหัสผ่าน'}, status=400)

        cache_key = f"odoo_session:{username}"
        cached_session = cache.get(cache_key)

        if cached_session:
            log_action("odoo_login", "cached", user_id=username)
            odoo_logger.info(f"[CACHE] Using cached session for {username}")
            return Response({
                'success': True,
                **cached_session
            })

        session_login_url = f"{os.getenv('ODOO_URL')}/web/session/authenticate"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "params": {
                "db": db,
                "login": username,
                "password": password
            }
        }

        res = requests.post(session_login_url, json=payload, headers=headers)
        if res.status_code != 200 or 'result' not in res.json():
            log_warning("odoo_login", "invalid credentials", user_id=username)
            odoo_logger.warning(f"Login failed for user={username}")
            return Response({'success': False, 'message': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status=401)

        result = res.json()['result']
        session_id = res.cookies.get('session_id')
        uid = result.get('uid')

        employee_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "hr.employee",
                "method": "search_read",
                "args": [[["user_id", "=", uid]]],
                "kwargs": {"fields": ["id", "name", "last_name", "job_id", "department_id"]}
            },
            "id": 1
        }

        employee_res = requests.post(
            f"{os.getenv('ODOO_URL')}/web/dataset/call_kw",
            json=employee_payload,
            headers=headers,
            cookies={'session_id': session_id}
        )

        employee_data = employee_res.json().get('result', [])
        employee_info = employee_data[0] if employee_data else {}
        employee_id = employee_info.get('id')
        name = employee_info.get('name')
        last_name = employee_info.get('last_name')
        job_id = employee_info.get('job_id', [None])[0]
        job_name = employee_info.get('job_id', [None, None])[1]
        department_id = employee_info.get('department_id', [None])[0]
        department_name = employee_info.get('department_id', [None, None])[1]



        user, _ = User.objects.get_or_create(username=f"odoo_user_{uid}")
        refresh = RefreshToken.for_user(user)
        refresh['uid'] = uid
        refresh['employee_id'] = employee_id
        refresh['session_id'] = session_id
        refresh['username'] = username

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        token = OdooJWTToken.objects.create(
            name=username,
            user_id=uid,
            session_id=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=1),
        )

        # origins = ['https://example.com']
        # for origin in origins:
        #     AllowedOrigin.objects.create(token=token, origin=origin)

        endpoints = ['/e-learning/read/', '/km/create/']
        for path in endpoints:
            AllowedEndpoint.objects.create(token=token, path=path)

        # PermissionScope.objects.create(
        #     token=token,
        #     model_name='hr.employee',
        #     can_create=False,
        #     can_read=True,
        #     can_update=False,
        #     can_delete=False
        # )

        response_data = {
            'access': access_token,
            'refresh': refresh_token,
            'session_id': session_id,
            'user_id': uid,
            'employee_id': employee_id,
            'name': name,
            'last_name': last_name,
            'job_id': job_id,
            'job_name': job_name,
            'department_id': department_id,
            'department_name': department_name,
            'user_context': result.get('user_context'),
            'db': db,
            'success': True
        }

        cache.set(cache_key, response_data, timeout=3600)
        log_action("odoo_login", "success", user_id=username, extra=f"uid={uid}")
        odoo_logger.info(f"User {username} logged in (uid={uid}, emp={employee_id})")

        return Response(response_data)

    except Exception as e:
        odoo_logger.exception(f"Unexpected error in odoo_login for username={request.data.get('username')}")
        return Response({'success': False, 'message': log_exception(e)}, status=500)