from django.urls import include, path
from django.contrib import admin


api_urls = [
    path('cdb_rest/', include('cdb_rest.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urls)),
]
