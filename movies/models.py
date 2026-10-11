from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Play(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    actors = models.ManyToManyField("Actor", related_name="plays", blank=True)
    genres = models.ManyToManyField("Genre", related_name="plays", blank=True)

    def __str__(self):
        return self.title


class Actor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class TheatreHall(models.Model):
    name = models.CharField(max_length=100)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(rows__gt=0), name="hall_rows_positive"),
            models.CheckConstraint(
                condition=models.Q(seats_in_row__gt=0),
                name="hall_seats_in_row_positive",
            ),
        ]

    def __str__(self):
        return self.name


class Performance(models.Model):
    play = models.ForeignKey(Play, on_delete=models.PROTECT, related_name="performances")
    theatre_hall = models.ForeignKey(
        TheatreHall, on_delete=models.PROTECT, related_name="performances"
    )
    show_time = models.DateTimeField()

    def __str__(self):
        return f"{self.play} at {self.show_time}"


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations"
    )

    def __str__(self):
        return f"Reservation {self.pk}"


class Ticket(models.Model):
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()
    performance = models.ForeignKey(
        Performance, on_delete=models.PROTECT, related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="tickets"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("performance", "row", "seat"),
                name="unique_seat_per_performance",
            ),
            models.CheckConstraint(condition=models.Q(row__gt=0), name="ticket_row_positive"),
            models.CheckConstraint(condition=models.Q(seat__gt=0), name="ticket_seat_positive"),
        ]

    def clean(self):
        super().clean()
        if self.performance_id and self.row is not None and self.seat is not None:
            hall = self.performance.theatre_hall
            errors = {}
            if self.row > hall.rows:
                errors["row"] = "This row does not exist in the performance's theatre hall."
            if self.seat > hall.seats_in_row:
                errors["seat"] = "This seat does not exist in the performance's theatre hall."
            if errors:
                raise ValidationError(errors)

    def __str__(self):
        return f"Row {self.row}, seat {self.seat} for {self.performance}"
