from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.models import LINEUser
from api.serializers.line_serializers import LINEUserSerializer
from api.utils.logger import log_exception

import base64
import uuid
from PIL import Image
import os

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