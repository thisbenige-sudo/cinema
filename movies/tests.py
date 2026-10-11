import json

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Actor, Genre, Performance, Play, Reservation, TheatreHall, Ticket


class TheatreModelTests(TestCase):
    def setUp(self):
        self.play = Play.objects.create(title="Hamlet")
        self.hall = TheatreHall.objects.create(name="Main Hall", rows=20, seats_in_row=15)
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now(),
        )
        self.user = get_user_model().objects.create_user(username="visitor")
        self.reservation = Reservation.objects.create(user=self.user)

    def test_play_has_many_actors_and_genres(self):
        actor = Actor.objects.create(first_name="Alex", last_name="Example")
        genre = Genre.objects.create(name="Drama")

        self.play.actors.add(actor)
        self.play.genres.add(genre)

        self.assertIn(self.play, actor.plays.all())
        self.assertIn(self.play, genre.plays.all())

    def test_ticket_must_be_within_the_hall_layout(self):
        ticket = Ticket(
            row=21,
            seat=1,
            performance=self.performance,
            reservation=self.reservation,
        )

        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_a_seat_can_only_be_ticketed_once_per_performance(self):
        Ticket.objects.create(
            row=3,
            seat=7,
            performance=self.performance,
            reservation=self.reservation,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ticket.objects.create(
                row=3,
                seat=7,
                performance=self.performance,
                reservation=self.reservation,
            )


class TheatreApiTests(TestCase):
    def setUp(self):
        self.play = Play.objects.create(title="Hamlet", description="A tragedy.")
        self.actor = Actor.objects.create(first_name="Alex", last_name="Example")
        self.genre = Genre.objects.create(name="Drama")
        self.play.actors.add(self.actor)
        self.play.genres.add(self.genre)
        self.hall = TheatreHall.objects.create(name="Main Hall", rows=2, seats_in_row=3)
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now(),
        )
        self.user = get_user_model().objects.create_user(username="api-visitor")

    def test_play_and_performance_lists(self):
        play_response = self.client.get("/api/plays/")
        performance_response = self.client.get("/api/performances/")

        self.assertEqual(play_response.status_code, 200)
        self.assertEqual(play_response.json()[0]["genres"], [{"id": self.genre.id, "name": "Drama"}])
        self.assertEqual(performance_response.status_code, 200)
        self.assertEqual(performance_response.json()[0]["theatre_hall"]["rows"], 2)

    def test_seat_availability_lists_booked_seats(self):
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=2,
            performance=self.performance,
            reservation=reservation,
        )

        response = self.client.get(f"/api/performances/{self.performance.id}/seats/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["booked_seats"], [{"row": 1, "seat": 2}])

    def test_reservation_requires_authentication(self):
        response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {"performance_id": self.performance.id, "seats": [{"row": 1, "seat": 1}]}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_reserve_multiple_seats(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {
                    "performance_id": self.performance.id,
                    "seats": [{"row": 1, "seat": 1}, {"row": 1, "seat": 2}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["tickets"],
            [{"row": 1, "seat": 1}, {"row": 1, "seat": 2}],
        )
        self.assertEqual(Reservation.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Ticket.objects.filter(reservation__user=self.user).count(), 2)

    def test_invalid_or_taken_seats_are_rejected_without_partial_reservations(self):
        self.client.force_login(self.user)
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=1,
            performance=self.performance,
            reservation=reservation,
        )

        taken_response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {
                    "performance_id": self.performance.id,
                    "seats": [{"row": 1, "seat": 1}, {"row": 1, "seat": 2}],
                }
            ),
            content_type="application/json",
        )
        invalid_response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {"performance_id": self.performance.id, "seats": [{"row": 3, "seat": 1}]}
            ),
            content_type="application/json",
        )

        self.assertEqual(taken_response.status_code, 409)
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(Reservation.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_seat_conflict_check_uses_exact_row_and_seat_pairs(self):
        self.client.force_login(self.user)
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            row=1,
            seat=2,
            performance=self.performance,
            reservation=reservation,
        )

        response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {
                    "performance_id": self.performance.id,
                    "seats": [{"row": 1, "seat": 1}, {"row": 2, "seat": 2}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
