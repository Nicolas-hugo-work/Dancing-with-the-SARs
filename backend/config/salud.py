from django.db import DatabaseError, connection
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


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
