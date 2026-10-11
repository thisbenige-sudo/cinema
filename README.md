# cinema

## Theatre booking data model

The `movies` app defines plays, actors, genres, theatre halls, performances,
reservations, and tickets. Plays have many-to-many relationships with actors
and genres. A reservation belongs to a Django user and groups tickets.

Tickets are unique by performance, row, and seat. Theatre hall dimensions and
ticket coordinates must be positive; `Ticket.full_clean()` also checks that the
selected row and seat exist in the performance's hall.

Create or apply database migrations with:

```sh
python manage.py makemigrations movies
python manage.py migrate
```
