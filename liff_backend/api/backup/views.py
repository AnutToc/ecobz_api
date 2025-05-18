from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

import logging

odoo_logger = logging.getLogger('odoo')

from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes, permission_classes, authentication_classes
from rest_framework.renderers import JSONRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import LINEUser, OdooJWTToken, AllowedEndpoint, PermissionScope, AllowedOrigin
from .line_serializers import LINEUserSerializer
from .utils.permissions import IsEndpointAllowed

from PIL import Image
import os
import uuid
import base64
import hashlib
import time
import requests
import json
import sys
import warnings
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore")
print(sys.version)

ODOO_DB = os.getenv('ODOO_DB')

def log_exception(e):
    traceback.print_exc()
    return str(e)

def odoo_rpc_call(session_id, model, method, args, call_id=1):
    url = f"{os.getenv('ODOO_URL')}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": {},
        },
        "id": call_id
    }
    cookies = {'session_id': session_id}
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, json=payload, headers=headers, cookies=cookies)
    return response.json()


def log_odoo_session_usage(user_id, session_id, action):
    print(f"[ODOO] User {user_id} using session '{session_id}' for action: {action}")

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['userId'],
        properties={
            'userId': openapi.Schema(type=openapi.TYPE_STRING),
            'displayName': openapi.Schema(type=openapi.TYPE_STRING),
            'pictureUrl': openapi.Schema(type=openapi.TYPE_STRING),
        }
    )
)
@api_view(['POST'])
def save_user(request):
    try:
        data = request.data
        user_id = data.get("userId")
        if not user_id:
            return Response({"error": "Missing userId"}, status=400)

        LINEUser.objects.update_or_create(
            user_id=user_id,
            defaults={
                "display_name": data.get("displayName", "Unknown"),
                "picture_url": data.get("pictureUrl", "")
            }
        )
        return Response({"message": "User saved successfully!"})
    except Exception as e:
        return Response({"error": log_exception(e)}, status=400)


@swagger_auto_schema(method='get', operation_description="Retrieve all stored LINE users.")
@api_view(['GET'])
def get_users(request):
    users = LINEUser.objects.all()
    serializer = LINEUserSerializer(users, many=True)
    return Response(serializer.data)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['image'],
        properties={
            'image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64 encoded JPEG image string")
        }
    )
)
@api_view(['POST'])
def save_image(request):
    try:
        image_data = request.data.get('image')
        if not image_data or not image_data.startswith("data:image/jpeg;base64,"):
            return Response({"error": "Invalid or missing image data"}, status=400)

        image_base64 = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
        img_name = uuid.uuid4().hex
        dir_name = 'imgs'
        os.makedirs(dir_name, exist_ok=True)

        original_path = os.path.join(dir_name, f'{img_name}.jpg')
        with open(original_path, 'wb') as f:
            f.write(image_bytes)

        original = Image.open(original_path)
        if original.format != 'JPEG':
            os.remove(original_path)
            return Response({"error": "Only JPEG images are supported."}, status=400)

        original.thumbnail((240, 240), Image.LANCZOS)
        thumbnail_path = os.path.join(dir_name, f'{img_name}_240.jpg')
        original.save(thumbnail_path, 'JPEG')

        return Response({"filename": img_name}, status=200)
    except Exception as e:
        return Response({"error": log_exception(e)}, status=400)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=[],
        properties={
            'allowed_origins': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING, format="uri"),
                description="Origin ที่อนุญาตให้เรียก API"
            ),
            'allowed_endpoints': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                description="รายการ endpoint ที่อนุญาต"
            ),
            'permission_scopes': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                description="สิทธิ์ในการเข้าถึง model ต่างๆ",
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'model_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'can_create': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'can_read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'can_update': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'can_delete': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'can_approve': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'can_reject': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            )
        },
        example={
            "allowed_origins": [
                "https://example.com"
            ],
            "allowed_endpoints": [
                "/api/erp/login/",
                "/api/erp/e-learning/read/",
                "/api/v1/auto/erp/purchase.order/read/",
                "/api/v1/auto/erp/purchase.order/approve/",
                "/api/v1/auto/erp/purchase.order/reject/"
            ],
            "permission_scopes": [
                {
                    "model_name": "purchase.order",
                    "can_create": True,
                    "can_read": True,
                    "can_update": False,
                    "can_delete": False,
                    "can_approve": True,
                    "can_reject": True
                }
            ]
        }
    ),
    responses={200: 'Permissions updated successfully'}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_token_permissions(request):
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response({'error': 'Authorization header missing or malformed'}, status=401)

        access_token = auth_header.split(" ")[1]
        token_record = OdooJWTToken.objects.filter(access_token=access_token).first()
        if not token_record:
            return Response({'error': 'Token not found in database'}, status=404)

        data = request.data

        AllowedOrigin.objects.filter(token=token_record).delete()
        AllowedEndpoint.objects.filter(token=token_record).delete()
        PermissionScope.objects.filter(token=token_record).delete()

        for origin in data.get('allowed_origins', []):
            AllowedOrigin.objects.create(token=token_record, origin=origin)

        for path in data.get('allowed_endpoints', []):
            AllowedEndpoint.objects.create(token=token_record, path=path)

        for scope in data.get('permission_scopes', []):
            PermissionScope.objects.create(
                token=token_record,
                model_name=scope.get('model_name'),
                can_create=scope.get('can_create', False),
                can_read=scope.get('can_read', False),
                can_update=scope.get('can_update', False),
                can_delete=scope.get('can_delete', False),
                can_approve=scope.get('can_approve', False),
                can_reject=scope.get('can_reject', False),
                
            )

        return Response({'status': 'success', 'message': 'Permissions updated successfully'})

    except Exception as e:
        return Response({'error': log_exception(e)}, status=500)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['refresh'],
        properties={
            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description="Current refresh token"),
            'days': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of days to extend token expiration", default=1)
        },
        example={
            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
            "days": 3
        }
    )
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def rotate_token(request):
    try:
        refresh_str = request.data.get("refresh")
        days = int(request.data.get("days", 1))

        if not refresh_str:
            return Response({"error": "Missing refresh token"}, status=400)

        if days < 1:
            return Response({"error": "Days must be at least 1"}, status=400)

        try:
            old_refresh = RefreshToken(refresh_str)
        except Exception:
            return Response({"error": "Invalid or expired refresh token"}, status=401)

        uid = old_refresh.get("uid")
        username = old_refresh.get("username")
        session_id = old_refresh.get("session_id")

        token_record = OdooJWTToken.objects.filter(refresh_token=refresh_str).first()
        if not token_record:
            return Response({"error": "Token not found"}, status=404)

        user = User.objects.get(username=f"odoo_user_{uid}")
        new_refresh = RefreshToken.for_user(user)
        new_refresh['uid'] = uid
        new_refresh['username'] = username
        new_refresh['session_id'] = session_id

        token_record.access_token = str(new_refresh.access_token)
        token_record.refresh_token = str(new_refresh)
        token_record.expires_at = timezone.now() + timedelta(days=days)
        token_record.save()

        return Response({
            "access": str(new_refresh.access_token),
            "refresh": str(new_refresh),
            "expires_at": token_record.expires_at.isoformat()
        })

    except Exception as e:
        return Response({'error': log_exception(e)}, status=500)


@swagger_auto_schema(
    method='get',
    security=[{'Bearer': []}],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def test_jwt(request):
    print("==== HEADERS ====")
    for k, v in request.headers.items():
        print(f"{k}: {v}")
    print("=================")

    jwt = JWTAuthentication()
    user_auth = jwt.authenticate(request)
    print("JWT AUTH RESULT:", user_auth)
    return Response({"status": "ok"})

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
        db = os.getenv('ODOO_DB')

        if not username or not password:
            odoo_logger.warning(f"Login failed: Missing credentials - username={username}")
            return Response({'success': False, 'message': 'กรุณาระบุชื่อผู้ใช้และรหัสผ่าน'}, status=400)

        cache_key = f"odoo_session:{username}"
        cached_session = cache.get(cache_key)

        if cached_session:
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
                "kwargs": {"fields": ["id", "name", "job_id", "department_id"]}
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
        department_name = employee_info.get('department_id', [None, None])[1]
        job_name = employee_info.get('job_id', [None, None])[1]


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

        origins = ['https://example.com', 'https://admin.example.com']
        for origin in origins:
            AllowedOrigin.objects.create(token=token, origin=origin)

        endpoints = ['/api/erp/login/', '/api/erp/e-learning/read']
        for path in endpoints:
            AllowedEndpoint.objects.create(token=token, path=path)

        PermissionScope.objects.create(
            token=token,
            model_name='hr.employee',
            can_create=True,
            can_read=True,
            can_update=False,
            can_delete=False
        )

        response_data = {
            'access': access_token,
            'refresh': refresh_token,
            'session_id': session_id,
            'user_id': uid,
            'employee_id': employee_id,
            'job_name': job_name,
            'department_name': department_name,
            'user_context': result.get('user_context'),
            'db': db,
            'success': True
        }

        cache.set(cache_key, response_data, timeout=3600)

        odoo_logger.info(f"User {username} logged in (uid={uid}, emp={employee_id})")

        return Response(response_data)

    except Exception as e:
        odoo_logger.exception(f"Unexpected error in odoo_login for username={request.data.get('username')}")
        return Response({'success': False, 'message': log_exception(e)}, status=500)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['session_id', 'user_id', 'employee_id', 'course_name'],
        properties={
            'session_id': openapi.Schema(type=openapi.TYPE_STRING, description="Session ID จากการ login"),
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="ชื่อพนักงาน"),
            'course_name': openapi.Schema(type=openapi.TYPE_STRING, description="ชื่อคอร์ส"),
            'course_department': openapi.Schema(type=openapi.TYPE_STRING, description="แผนกคอร์ส"),
            'course_progress': openapi.Schema(type=openapi.TYPE_STRING, description="ความคืบหน้าคอร์ส")
        },
        responses={
            200: openapi.Response("สร้างข้อมูลสำเร็จ", openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'elearning_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )),
            400: "ข้อมูลไม่ถูกต้อง"
        }
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_elearning_create(request):
    try:
        data = request.data

        for key in ['user_id', 'session_id', 'employee_id']:
            if key not in data:
                return JsonResponse({'status': 'error', 'message': f'Missing key: {key}'}, status=400)

        log_odoo_session_usage(data['user_id'], data['session_id'], "Create E-learning")

        res = odoo_rpc_call(
            session_id=data['session_id'],
            model='hr.employee',
            method='create',
            args=[[{
                'name': data['name'],
                'course_name': data.get('course_name'),
                'course_department': data.get('course_department'),
                'course_progress': data.get('course_progress')
            }]]
        )

        if 'error' in res:
            return JsonResponse({
                'status': 'error',
                'message': res['error'].get('message', 'Unknown Odoo error')
            }, status=400)

        return JsonResponse({
            'status': 'success',
            'elearning_id': res['result']
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': log_exception(e)
        }, status=400)

@swagger_auto_schema(
    method='get',
    security=[{'Bearer': []}],
    manual_parameters=[
        openapi.Parameter('employee_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="รหัสพนักงาน")
    ],
    responses={
        200: openapi.Response("ดึงข้อมูลสำเร็จ", openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING),
                'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'course_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'course_department': openapi.Schema(type=openapi.TYPE_STRING),
                        'course_progress': openapi.Schema(type=openapi.TYPE_STRING),
                        'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                ))
            }
        )),
        400: "ข้อมูลไม่ถูกต้อง"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_elearning_read(request):
    try:
        print("Authorization header:", request.headers.get('Authorization'))
        jwt = JWTAuthentication()
        user, validated_token = jwt.authenticate(request)
        print("Authentication result:", user, validated_token)

        session_id = validated_token['session_id']
        user_id = validated_token['uid']
        employee_id = request.GET.get('employee_id')

        domain = [('id', '=', int(employee_id))] if employee_id else []

        log_odoo_session_usage(user_id, session_id, "Read E-learning")

        res = odoo_rpc_call(
            session_id=session_id,
            model='hr.employee',
            method='search_read',
            args=[domain, ['course_name', 'course_department', 'course_progress']]
        )

        return JsonResponse({'status': 'success', 'data': res['result']})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)

@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['session_id', 'user_id', 'elearning_id'],
        properties={
            'session_id': openapi.Schema(type=openapi.TYPE_STRING, description="Session ID จากการ login"),
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="User ID จากการ login"),
            'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="รหัส E-learning"),
            'course_name': openapi.Schema(type=openapi.TYPE_STRING, description="ชื่อคอร์ส"),
            'course_department': openapi.Schema(type=openapi.TYPE_STRING, description="แผนกคอร์ส"),
            'course_progress': openapi.Schema(type=openapi.TYPE_STRING, description="ความคืบหน้าคอร์ส")
        },
        responses={
            200: openapi.Response("อัปเดตข้อมูลสำเร็จ", openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'updated': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                }
            )),
            400: "ข้อมูลไม่ถูกต้อง"
        }
    )
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_elearning_update(request):
    try:
        data = request.data
        log_odoo_session_usage(data['user_id'], data['session_id'], "Update E-learning")
        update_fields = {}
        for key in ['course_name', 'course_department', 'course_progress']:
            if key in data:
                update_fields[key] = data[key]

        res = odoo_rpc_call(
            session_id=data['session_id'],
            model='hr.employee',
            method='write',
            args=[[int(data['employee_id'])], update_fields]
        )
        return JsonResponse({'status': 'success', 'updated': res})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)

@swagger_auto_schema(
    method='delete',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['session_id', 'user_id', 'employee_id'],
        properties={
            'session_id': openapi.Schema(type=openapi.TYPE_STRING, description="Session ID จากการ login"),
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="User ID จากการ login"),
            'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="รหัส E-learning")
        },
        responses={
            200: openapi.Response("ลบข้อมูลสำเร็จ", openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'deleted': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                }
            )),
            400: "ข้อมูลไม่ถูกต้อง"
        }
    )
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_elearning_delete(request):
    try:
        data = request.data
        log_odoo_session_usage(data['user_id'], data['session_id'], "Delete E-learning")
        res = odoo_rpc_call(
            uid=data['user_id'],
            session_id=data['session_id'],
            model='hr.employee',
            method='unlink',
            args=[[int(data['elearning_id'])]]
        )
        return JsonResponse({'status': 'success', 'deleted': res['result']})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['session_id', 'user_id'],
        properties={
            'session_id': openapi.Schema(type=openapi.TYPE_STRING),
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'po_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'po_name': openapi.Schema(type=openapi.TYPE_STRING),
        }
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_approve_po(request):
    try:
        data = request.data
        session_id = data['session_id']
        user_id = int(data['user_id'])
        po_id = data.get('po_id')
        po_name = data.get('po_name')
        log_odoo_session_usage(user_id, session_id, f"Approve PO (ID: {po_id or po_name})")
        if po_id:
            res = odoo_rpc_call(
                session_id=data['session_id'],
                model='purchase.order',
                method='button_confirm_approve',
                args=[[po_id]]
            )
        elif po_name:
            search = odoo_rpc_call(user_id, session_id, 'purchase.order', 'search', [[['name', '=', po_name]]])
            res = odoo_rpc_call(user_id, session_id, 'purchase.order', 'button_confirm_approve', [[search['result']]])
        else:
            return JsonResponse({'status': 'error', 'message': 'Missing po_id or po_name'}, status=400)

        return JsonResponse({'status': 'success', 'message': 'PO approved successfully', 'output': res})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)
