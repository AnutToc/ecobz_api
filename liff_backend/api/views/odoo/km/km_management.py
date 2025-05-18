from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.utils.permissions import IsEndpointAllowed
from api.utils.logger import log_action, log_warning, log_exception
from api.utils.odoo import odoo_rpc_call, log_odoo_session_usage
from rest_framework_simplejwt.authentication import JWTAuthentication


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['session_id', 'user_id', 'course_id', 'student_name', 'analytics'],
        properties={
            'session_id': openapi.Schema(type=openapi.TYPE_STRING, description="Session ID จากการ login"),
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="User ID"),
            'course_id': openapi.Schema(type=openapi.TYPE_STRING, description="รหัสคอร์ส"),
            'courseName': openapi.Schema(type=openapi.TYPE_STRING, description="ชื่อคอร์ส (ชื่อใน UI)"),
            'student_name': openapi.Schema(type=openapi.TYPE_STRING, description="ชื่อผู้เรียน"),
            'status': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="สถานะการลงทะเบียน"),
            'analytics': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="ข้อมูล analytics",
                additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
            ),
            'createdAt': openapi.Schema(type=openapi.TYPE_OBJECT),
            'updatedAt': openapi.Schema(type=openapi.TYPE_OBJECT),
        },
        example={
            "session_id": "abc123",
            "course_id": "1",
            "courseName": "7 Wastes (Intermediate)",
            "student_name": "Test",
            "user_id": "1",
            "status": False,
            "analytics": {
                "total": 0,
                "pending": 0,
                "processing": 0,
                "complete": 0,
                "status": "pending",
                "message": "Not started",
                "post": {"req": False, "measure": None, "result": False},
                "pre": {"req": False, "measure": None, "result": False},
                "retest": {"req": False, "measure": None, "result": False},
                "option": {"cert_area": None, "exam_round": None},
                "percent": 0
            },
            "createdAt": {"$date": "2025-04-24T03:03:41.956Z"},
            "updatedAt": {"$date": "2025-04-24T03:03:41.956Z"}
        }
    ),
    responses={
        200: openapi.Response("ส่งข้อมูลสำเร็จ", openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING),
                'result': openapi.Schema(type=openapi.TYPE_OBJECT)
            }
        )),
        400: "ข้อมูลไม่ถูกต้อง"
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEndpointAllowed])
def odoo_km_create(request):
    try:
        data = request.data
        required_fields = ['session_id', 'user_id', 'course_id', 'student_name', 'analytics']
        for field in required_fields:
            if field not in data:
                log_warning("kovic.km", f"missing field: {field}", user_id=data.get('user_id'))
                return JsonResponse({'status': 'error', 'message': f'Missing field: {field}'}, status=400)

        log_action("elearning.analytics", "sync", user_id=data['user_id'])
        log_odoo_session_usage(data['user_id'], data['session_id'], "Sync E-learning Analytics")

        payload = {
            'user_id': str(data['user_id']),
            'course_id': data['course_id'],
            'student_name': data['student_name'],
            'analytics': data['analytics']
        }

        if 'status' in data:
            payload['status'] = data['status']
        if 'courseName' in data:
            payload['course_name'] = data['courseName']
        if 'createdAt' in data:
            payload['created_at'] = data['createdAt']
        if 'updatedAt' in data:
            payload['updated_at'] = data['updatedAt']

        res = odoo_rpc_call(
            session_id=data['session_id'],
            model='kovic.km.enrollment',
            method='create_enrollment_from_api',
            args=[payload]
        )

        log_action("kovic.km", f"Odoo response: {res}", user_id=data['user_id'])

        if 'error' in res:
            log_warning("kovic.km", f"Odoo error: {res['error']}", user_id=data['user_id'])
            return JsonResponse({
                'status': 'error',
                'odoo_error': res['error'],
                'message': res['error'].get('message', 'Unknown Odoo error')
            }, status=400)

        return JsonResponse({
            'status': 'success',
            'result': res['result']
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)