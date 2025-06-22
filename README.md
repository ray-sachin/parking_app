# Parking Management Project

This is a Flask-based web application for managing parking lots, user bookings, and administrative operations. It includes both a web frontend and JSON API endpoints for integrations.

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.10+** (check with `python --version`)
- **pip** (comes bundled with Python)
- **virtualenv** (optional but recommended)

---

## Installation & Setup

1. **Create and activate a virtual environment** (recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate       # On macOS/Linux
   venv\Scripts\activate.bat    # On Windows
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**

   - Copy the example configuration file if provided, or set environment variables:

     ```bash
     export FLASK_APP=app.py
     export FLASK_ENV=development
     export DATABASE_URL=sqlite:///parking_app.db   # or your preferred database URI
     ```

   - (Optional) If using a different database, update the `DATABASE_URL` environment variable accordingly.

---

## Running the Application

Start the Flask development server:

```bash
flask run
```

By default, the application will be available at `http://localhost:5000`.

---

## API Endpoints

A full OpenAPI (Swagger) specification is provided in `openapi.yaml`.

- **Get all parking stats**

  ```http
  GET /api/parking-stats
  ```

- **Get available spots for a specific parking lot**

  ```http
  GET /api/available-spots/{id}
  ```

Use `curl`, Postman, or any HTTP client to interact with these endpoints.

---

## Frontend

- **Templates:** The frontend HTML templates are under `parking_app_23f2002518/templates/`.
- **Static Assets:** CSS, JavaScript, and images are in `parking_app_23f2002518/static/`.

Navigate to `http://localhost:5000` in your browser to use the web UI.

---

## Further Development

- Add routes for viewing your parking spots on maps.
- Implement user role permissions (e.g., admins can delete the user data or a user can delete his account).
- Secure API endpoints with token-based authentication.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.