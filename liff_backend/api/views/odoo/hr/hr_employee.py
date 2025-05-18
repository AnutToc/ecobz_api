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
                log_warning("elearning", f"missing key: {key}", user_id=data.get('user_id'))
                return JsonResponse({'status': 'error', 'message': f'Missing key: {key}'}, status=400)

        log_action("elearning", "create", user_id=data['user_id'])
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
            log_warning("elearning", f"odoo error: {res['error'].get('message')}", user_id=data['user_id'])
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
        
        log_action("elearning", "read", user_id=user_id)
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
        
        log_action("elearning", "update", user_id=data.get('user_id'), extra=f"id={data.get('employee_id')}")
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
        log_action("elearning", "delete", user_id=data.get('user_id'), extra=f"id={data.get('employee_id')}")
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