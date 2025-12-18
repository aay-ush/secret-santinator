# secret-santinator
LLM-assisted Software Engineering. LLM provides the legacy code to build and bugfix for real production experience!

## Render DB Init
```sh
python -c "from wsgi import app; from app.extensions import db; from app.models import AssignmentState; app.app_context().push(); db.create_all(); AssignmentState.get_singleton(); print('DB initialized')"
```
 - (todo) flask db init/migrate/upgrade


## Steps
 1. Deploy on Render
 2. Visit /auth/register and register admin (SANTA_ADMIN_NAME value in render.yaml)
 3. Login as admin and hit:
     - Dashboard > Run & lock assignments
 4. Participants login: /auth/login > name > stored passphrase > see assignment
 5. If someone loses passphrase:
     - Login > request reset
     - Admin goes to Dashboard > Reset requests > Reset now (after confirmation)
