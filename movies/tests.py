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
