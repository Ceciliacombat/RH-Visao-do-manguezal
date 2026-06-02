from visao_do_manguezal import create_app
from visao_do_manguezal.extensions import db
from visao_do_manguezal.models import Usuario
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    admin = Usuario(
        username="admin",
        senha=generate_password_hash("1234"),
        tipo="admin"
    )

    db.session.add(admin)
    db.session.commit()

    print("Admin criado!")