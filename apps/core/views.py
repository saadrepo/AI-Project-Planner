from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "base.html")


def health_check(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        database_ok = cursor.fetchone() == (1,)
    return JsonResponse({"status": "ok", "database": "ok" if database_ok else "error"})
