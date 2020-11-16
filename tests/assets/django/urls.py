from django.contrib import admin
from django.urls import path  # type:ignore

urlpatterns = [
    path("admin/", admin.site.urls),
]
