# cinema

## Run locally

Requirements: Python 3.13 and pip.

1. Clone the repository and enter its directory:

   ```sh
   git clone <repository-url>
   cd cinema
   ```

2. Create and activate a virtual environment:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows, activate it with `.venv\Scripts\activate`.

3. Install Django:

   ```sh
   python -m pip install Django==6.1.1
   ```

4. Create the local SQLite database and an admin account:

   ```sh
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. Start the development server:

   ```sh
   python manage.py runserver
   ```

The API is then available at `http://127.0.0.1:8000/api/`. Sign in to
`http://127.0.0.1:8000/admin/` with the superuser account and add plays,
actors, genres, halls, and performances before browsing; list endpoints are
empty until records have been added.

Run the test suite with:

```sh
python manage.py test
```

Example API and Docker run screenshots:

![Cinema API example](https://media.mate.academy/cinema_api.png)

![Run with Docker example](https://media.mate.academy/run_with_docker.png)

Docker configuration is not currently included in this repository; use the
local Python steps above.

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

## Features

![Theatre API features](https://media.mate.academy/features.png)

- Browse plays with their descriptions, actors, and genres.
- View scheduled performances, show times, and theatre hall layouts.
- Check which seats are already booked for a performance.
- Reserve multiple seats for a performance in one request.
- View your own reservations after signing in.
- Reject invalid seat selections and duplicate bookings.

## Use the API

### Browse plays, performances, and seat availability

Open these URLs in a browser, or request them with `curl`:

```sh
curl http://127.0.0.1:8000/api/plays/
curl http://127.0.0.1:8000/api/performances/
```

Choose a performance ID from the performances response and check its booked
seats. The response includes the hall dimensions; select seats within those
dimensions that are not in `booked_seats`.

```sh
curl http://127.0.0.1:8000/api/performances/1/seats/
```

### Reserve seats in the local development environment

The reservation API requires an authenticated Django session. There is not yet
a public registration or login endpoint, nor a visitor-facing booking website.
For a local demonstration only, sign in at `http://127.0.0.1:8000/admin/`
using the superuser created during setup. Never share or use a superuser
account for visitors on a deployed site.

1. Open the browser developer console on the same local site after signing in.
   Replace `1` with the performance ID you chose and update the row and seat
   numbers:

   ```javascript
   const csrfToken = decodeURIComponent(
     document.cookie
       .split("; ")
       .find((cookie) => cookie.startsWith("csrftoken="))
       .split("=")[1],
   );

   fetch("/api/reservations/", {
     method: "POST",
     credentials: "same-origin",
     headers: {
       "Content-Type": "application/json",
       "X-CSRFToken": csrfToken,
     },
     body: JSON.stringify({
       performance_id: 1,
       seats: [
         { row: 5, seat: 1 },
         { row: 5, seat: 2 },
       ],
     }),
   }).then(async (response) => ({
     status: response.status,
     body: await response.json(),
   }));
   ```

   A successful booking returns `201 Created` with the reservation and tickets.
   Invalid seats return `400 Bad Request`; seats booked by someone else return
   `409 Conflict`. Check availability again before selecting different seats.
2. View reservations for the signed-in user at
   `http://127.0.0.1:8000/api/reservations/` in the same browser session.

Reservation endpoints require a signed-in user. Browser clients must send the
Django session cookie and `X-CSRFToken` header. Password-based token or
third-party API authentication is not currently configured. Before visitors
can sign in and book on a deployed site, add a public authentication flow and
a booking UI or provide another secure client that manages Django sessions;
do not give visitors staff or superuser access to work around this limitation.

### Run tests

```sh
python manage.py test
```

## REST API reference

All paths are relative to `http://127.0.0.1:8000/api/`:

- `GET /plays/` — lists plays with actors and genres.
- `GET /performances/` — lists scheduled performances and hall layouts.
- `GET /performances/<id>/seats/` — returns hall dimensions and booked seats.
- `GET /reservations/` — lists the signed-in user's reservations.
- `POST /reservations/` — creates a reservation for one or more seats.

The reservation request body is JSON:

```json
{
  "performance_id": 1,
  "seats": [{"row": 5, "seat": 1}, {"row": 5, "seat": 2}]
}
```
