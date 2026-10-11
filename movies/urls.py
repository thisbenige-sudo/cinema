from django.urls import path

from . import api_views


urlpatterns = [
    path("plays/", api_views.plays, name="api-plays"),
    path("performances/", api_views.performances, name="api-performances"),
    path(
        "performances/<int:performance_id>/seats/",
        api_views.performance_seats,
        name="api-performance-seats",
    ),
    path("reservations/", api_views.reservations, name="api-reservations"),
]
