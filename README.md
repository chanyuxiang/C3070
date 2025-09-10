1) clone
git clone https://github.com/<YOUR-USERNAME>/<YOUR-REPO>.git
cd <YOUR-REPO>

2) create and activate venv
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

3) install deps
pip install -r requirements.txt

4) migrate DB
python c3070_final/manage.py makemigrations
python c3070_final/manage.py migrate

5) create superuser (for admin)
python c3070_final/manage.py createsuperuser

6) run dev server
python c3070_final/manage.py runserver

7) Testing of information
python manage.py test core.tests -v 2
