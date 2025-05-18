from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.utils.logger import log_exception, log_action, log_warning
from api.utils.odoo import odoo_rpc_call, log_odoo_session_usage
from api.utils.permissions import IsEndpointAllowed

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
        
        log_action("purchase_order", "approve", user_id=user_id, extra=f"po_id={po_id}, po_name={po_name}")
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
            log_warning("purchase_order", "missing po_id or po_name", user_id=user_id)
            return JsonResponse({'status': 'error', 'message': 'Missing po_id or po_name'}, status=400)

        return JsonResponse({'status': 'success', 'message': 'PO approved successfully', 'output': res})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': log_exception(e)}, status=400)
