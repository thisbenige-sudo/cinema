import json

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import Performance, Play, Reservation, Ticket


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def plays(request):
    if request.method != "GET":
        return _error("Method not allowed.", 405)

    items = [
        {
            "id": play.id,
            "title": play.title,
            "description": play.description,
            "actors": [
                {"id": actor.id, "first_name": actor.first_name, "last_name": actor.last_name}
                for actor in play.actors.all()
            ],
            "genres": [{"id": genre.id, "name": genre.name} for genre in play.genres.all()],
        }
        for play in Play.objects.prefetch_related("actors", "genres").order_by("title")
    ]
    return JsonResponse(items, safe=False)


def performances(request):
    if request.method != "GET":
        return _error("Method not allowed.", 405)

    items = [
        {
            "id": performance.id,
            "play": {"id": performance.play_id, "title": performance.play.title},
            "theatre_hall": {
                "id": performance.theatre_hall_id,
                "name": performance.theatre_hall.name,
                "rows": performance.theatre_hall.rows,
                "seats_in_row": performance.theatre_hall.seats_in_row,
            },
            "show_time": performance.show_time.isoformat(),
        }
        for performance in Performance.objects.select_related("play", "theatre_hall").order_by(
            "show_time"
        )
    ]
    return JsonResponse(items, safe=False)


def performance_seats(request, performance_id):
    if request.method != "GET":
        return _error("Method not allowed.", 405)

    performance = get_object_or_404(
        Performance.objects.select_related("theatre_hall"), pk=performance_id
    )
    booked_seats = list(
        performance.tickets.order_by("row", "seat").values("row", "seat")
    )
    return JsonResponse(
        {
            "performance_id": performance.id,
            "rows": performance.theatre_hall.rows,
            "seats_in_row": performance.theatre_hall.seats_in_row,
            "booked_seats": booked_seats,
        }
    )


def reservations(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return _error("Authentication required.", 401)

        items = [
            {
                "id": reservation.id,
                "created_at": reservation.created_at.isoformat(),
                "tickets": [
                    {
                        "row": ticket.row,
                        "seat": ticket.seat,
                        "performance_id": ticket.performance_id,
                    }
                    for ticket in reservation.tickets.select_related("performance").order_by(
                        "performance_id", "row", "seat"
                    )
                ],
            }
            for reservation in Reservation.objects.filter(user=request.user).order_by(
                "-created_at"
            )
        ]
        return JsonResponse(items, safe=False)

    if request.method != "POST":
        return _error("Method not allowed.", 405)
    if not request.user.is_authenticated:
        return _error("Authentication required.", 401)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("Request body must contain valid JSON.", 400)

    if not isinstance(payload, dict):
        return _error("Request body must be a JSON object.", 400)

    performance_id = payload.get("performance_id")
    seats = payload.get("seats")
    if type(performance_id) is not int or not isinstance(seats, list) or not seats:
        return _error("Provide an integer performance_id and a non-empty seats list.", 400)

    normalized_seats = []
    for seat in seats:
        if (
            not isinstance(seat, dict)
            or type(seat.get("row")) is not int
            or type(seat.get("seat")) is not int
            or seat["row"] < 1
            or seat["seat"] < 1
        ):
            return _error("Each seat must have positive integer row and seat values.", 400)
        normalized_seats.append((seat["row"], seat["seat"]))

    if len(normalized_seats) != len(set(normalized_seats)):
        return _error("The seats list contains duplicates.", 400)

    performance = get_object_or_404(
        Performance.objects.select_related("theatre_hall"), pk=performance_id
    )
    hall = performance.theatre_hall
    if any(row > hall.rows or seat > hall.seats_in_row for row, seat in normalized_seats):
        return _error("One or more seats are outside the theatre hall layout.", 400)

    selected_seats_query = Q()
    for row, seat in normalized_seats:
        selected_seats_query |= Q(row=row, seat=seat)
    if Ticket.objects.filter(performance=performance).filter(selected_seats_query).exists():
        return _error("One or more selected seats are already booked.", 409)

    try:
        with transaction.atomic():
            reservation = Reservation.objects.create(user=request.user)
            Ticket.objects.bulk_create(
                [
                    Ticket(
                        row=row,
                        seat=seat,
                        performance=performance,
                        reservation=reservation,
                    )
                    for row, seat in normalized_seats
                ]
            )
    except IntegrityError:
        return _error("One or more selected seats are no longer available.", 409)

    return JsonResponse(
        {
            "id": reservation.id,
            "created_at": reservation.created_at.isoformat(),
            "performance_id": performance.id,
            "tickets": [{"row": row, "seat": seat} for row, seat in normalized_seats],
        },
        status=201,
    )
