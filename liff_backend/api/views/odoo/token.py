from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.contrib.auth.models import User
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.models import OdooJWTToken, AllowedOrigin, AllowedEndpoint, PermissionScope
from api.utils.logger import log_action, log_warning, log_exception
from api.utils.permissions import IsEndpointAllowed
from datetime import timedelta


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
                "/login/",
                "/e-learning/read/",
                "/v1/auto/erp/purchase.order/read/",
                "/v1/auto/erp/purchase.order/approve/",
                "/v1/auto/erp/purchase.order/reject/"
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
            log_warning("token", "token not found", extra=access_token)
            return Response({'error': 'Token not found in database'}, status=404)

        log_action("token", "setup_permissions", user_id=token_record.user_id)
        data = request.data

        AllowedOrigin.objects.filter(token=token_record).delete()
        for origin in data.get('allowed_origins', []):
            AllowedOrigin.objects.create(token=token_record, origin=origin)

        AllowedEndpoint.objects.filter(token=token_record).delete()
        for path in data.get('allowed_endpoints', []):
            AllowedEndpoint.objects.create(token=token_record, path=path)

        PermissionScope.objects.filter(token=token_record).delete()
        for scope in data.get('permission_scopes', []):
            model = scope.get('model_name')
            if not model:
                continue
            PermissionScope.objects.create(
                token=token_record,
                model_name=model,
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
    method='patch',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'allowed_origins': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING)
            ),
            'allowed_endpoints': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING)
            ),
            'permission_scopes': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=['model_name'],
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
                "/login/",
                "/e-learning/read/",
                "/v1/auto/erp/purchase.order/read/",
                "/v1/auto/erp/purchase.order/approve/",
                "/v1/auto/erp/purchase.order/reject/"
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
    operation_description="อัปเดต allowed_origins, allowed_endpoints และ permission_scopes สำหรับ token ที่กำหนด"
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_permission_scope(request):
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        token_record = OdooJWTToken.objects.filter(access_token=token).first()
        if not token_record:
            log_warning("permission", "token not found for patch")
            return Response({"error": "Token not found"}, status=404)

        data = request.data

        if 'allowed_origins' in data:
            for origin in data['allowed_origins']:
                if not AllowedOrigin.objects.filter(token=token_record, origin=origin).exists():
                    AllowedOrigin.objects.create(token=token_record, origin=origin)

        if 'allowed_endpoints' in data:
            for endpoint in data['allowed_endpoints']:
                if not AllowedEndpoint.objects.filter(token=token_record, path=endpoint).exists():
                    AllowedEndpoint.objects.create(token=token_record, path=endpoint)

        if 'permission_scopes' in data:
            for scope in data['permission_scopes']:
                model = scope.get('model_name')
                if not model:
                    continue
                obj, created = PermissionScope.objects.get_or_create(
                    token=token_record,
                    model_name=model
                )
                updated = False
                for field in ["can_create", "can_read", "can_update", "can_delete", "can_approve", "can_reject"]:
                    if field in scope and getattr(obj, field) != scope[field]:
                        setattr(obj, field, scope[field])
                        updated = True
                if updated:
                    obj.save()


        log_action("permission", "patched_replace", user_id=token_record.user_id)
        return Response({"status": "success", "message": "Permissions updated"})

    except Exception as e:
        return Response({"error": log_exception(e)}, status=500)
    
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
            log_warning("token", "missing refresh token")
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
        
        log_action("token", "rotate", user_id=uid)
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