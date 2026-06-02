from visao_do_manguezal import create_app
from visao_do_manguezal.extensions import db

# 👇 IMPORTANTE (ISSO RESOLVE)
from visao_do_manguezal.models import Usuario

app = create_app()

with app.app_context():
    db.create_all()
    print("Banco criado!")