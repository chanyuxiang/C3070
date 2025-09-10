# Identity and Profile Management API

This project is a Django + Django REST Framework (DRF) application that provides a **context-aware, role-based identity and profile management API**.  
It supports multiple identity contexts (e.g., Legal, Social, Work), multilingual name fields, and a simple web frontend built with Bootstrap + JavaScript.

---

## Features
- **User Registration & Login** (JWT authentication using `djangorestframework-simplejwt`)
- **Role-Based Access Control** (`admin` vs `user`)
- **Manage Multiple Identities** (per context and language)
- **Preferred Identity Selection** for profile display
- **Public Name Lookup Tool** (context + language aware)
- **Bulk Import & Export of Identities** (JSON)
- **Bootstrap Frontend** (login, register, home, profile pages)
- **Security**: stateless JWT, ownership checks, input normalization

---

## Prerequisites
- Python **3.12+**
- pip (latest)
- Git (to clone repository)

---

## Setup Instructions

1. **Clone this repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python c3070_final/manage.py migrate
   ```

5. **Create a superuser (admin account)**
   ```bash
   python c3070_final/manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python c3070_final/manage.py runserver
   ```

7. **Access the application**
   - Homepage: [http://127.0.0.1:8000/api/home/](http://127.0.0.1:8000/api/home/)  
   - Admin Panel: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Testing

Run automated tests with:

```bash
python c3070_final/manage.py test core.tests -v 2
```

This covers:
- Identity CRUD operations
- Role-based filtering
- Profile updates
- Import/export JSON

---

## Project Structure
```
c3070_final/       # Main Django project folder
  core/            # Core app with models, views, serializers, tests
  templates/       # HTML templates (login, home, profile, etc.)
  static/          # CSS and JS (Bootstrap, main.js)
requirements.txt   # Python dependencies
README.md          # This file
```

---

## Example Import/Export JSON

### Export (GET `/api/identities/export/`)
```json
{
  "items": [
    {"display_name":"陈", "context":"Legal", "language":"zh"},
    {"display_name":"Chan Yu Xiang", "context":"Legal", "language":"en"}
  ]
}
```

### Import (POST `/api/identities/import/`)
```json
{
  "items": [
    {"display_name": "Jonathan", "context": "School", "language": "en"},
    {"display_name": "李伟明", "context": "Social", "language": "zh"}
  ]
}
```

---

## License
This project is for educational use under the University of London CM3070 final project submission.
