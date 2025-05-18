from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models import OdooJWTToken, PermissionScope
from api.permissions import IsEndpointAllowed
from api.utils.logger import log_action, log_exception, log_warning
from api.utils.security import is_host_allowed

import os
import requests


class AutoResolverAPI(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsEndpointAllowed]

    def resolve_model(self, module):
        return module

    def resolve_permission(self, token, model, action):
        scope = PermissionScope.objects.filter(token=token, model_name=model).first()
        if not scope:
            log_warning("auto_resolver", "unauthorized access")
            return False
        return {
            "create": scope.can_create,
            "read": scope.can_read,
            "update": scope.can_update,
            "delete": scope.can_delete,
            "approve": scope.can_approve,
            "reject": scope.can_reject,
        }.get(action, False)

    def odoo_rpc(self, session_id, model, method, args):
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
            "id": 1
        }
        headers = {'Content-Type': 'application/json'}
        cookies = {'session_id': session_id}
        return requests.post(url, json=payload, headers=headers, cookies=cookies).json()

    def post(self, request, channel, module, action, res_id=None):
        try:
            version = request.version
            jwt = JWTAuthentication()
            user_auth = jwt.authenticate(request)
            if not user_auth:
                log_warning("auto_resolver", "unauthorized access")
                return Response({"error": "Unauthorized"}, status=401)

            user, validated_token = user_auth
            session_id = validated_token.get("session_id")
            uid = validated_token.get("uid")

            token_record = OdooJWTToken.objects.filter(access_token=str(validated_token)).first()
            if not token_record:
                log_warning("auto_resolver", "token not found", user_id=uid)
                return Response({"error": "Token not found"}, status=401)
            
            if not is_host_allowed(request, token_record, uid=uid):
                return Response({"error": "Unauthorized host"}, status=403)
            
            model = self.resolve_model(module)
            if not model:
                log_warning("auto_resolver", f"unknown model: {module}", user_id=uid)
                return Response({"error": f"Unknown model: {module}"}, status=404)

            if not self.resolve_permission(token_record, model, action):
                log_warning("auto_resolver", f"permission denied: {action}", user_id=uid, extra=f"model={model}")
                return Response({"error": "Permission denied"}, status=403)

            log_action("auto_resolver", action, user_id=uid, extra=f"model={model}, res_id={res_id}")
            
            method_map = {
                "create": "create",
                "read": "search_read",
                "update": "write",
                "delete": "unlink",
                "approve": "button_confirm_approve",
                "reject": "button_reject",
            }

            if action not in method_map:
                log_warning("auto_resolver", f"unsupported action: {action}", user_id=uid)
                return Response({"error": "Unsupported action"}, status=400)

            odoo_method = method_map[action]

            if action == "create":
                args = [[request.data]]
            elif action == "read":
                domain = [('id', '=', int(res_id))] if res_id else []
                fields = ['id', 'name']
                if model == 'hr.employee':
                    fields += ['job_id', 'department_id']
                elif model == 'purchase.order':
                    fields += ['state']
                args = [domain, fields]
            elif action == "update":
                if not res_id:
                    log_warning("auto_resolver", "missing res_id for update", user_id=uid)
                    return Response({"error": "res_id is required for update"}, status=400)
                args = [[int(res_id)], request.data]
            elif action == "delete":
                if not res_id:
                    log_warning("auto_resolver", "missing res_id for delete", user_id=uid)
                    return Response({"error": "res_id is required for delete"}, status=400)
                args = [[int(res_id)]]
            elif action in ["approve", "reject"]:
                if not res_id:
                    log_warning("auto_resolver", f"missing res_id for {action}", user_id=uid)
                    return Response({"error": "res_id is required for approve/reject"}, status=400)
                args = [[int(res_id)]]

            result = self.odoo_rpc(session_id, model, odoo_method, args)

            return Response({
                "status": "success",
                "odoo_method": odoo_method,
                "result": result.get("result")
            }, status=200)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
