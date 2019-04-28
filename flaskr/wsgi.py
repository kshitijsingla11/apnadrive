from . import create_app
from . import db
app = create_app()
with app.app_context():
    db.init_db()