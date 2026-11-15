from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

RESPUESTA_DE_ESTADO = inline_serializer(
    "Estado", {"estado": serializers.ChoiceField(["ok", "no_disponible"])}
)


@extend_schema(
    summary="Estado del servicio y de la base de datos",
    responses={200: RESPUESTA_DE_ESTADO, 503: RESPUESTA_DE_ESTADO},
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def healthz(request):
    """Comprueba que el servicio responde y alcanza la base de datos; 503 sin detalle si no."""
    if base_de_datos_disponible():
        return Response({"estado": "ok"})
    return Response({"estado": "no_disponible"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def base_de_datos_disponible() -> bool:
    try:
        connection.ensure_connection()
    except DatabaseError:
        return False
    return True
