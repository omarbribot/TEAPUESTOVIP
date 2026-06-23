# recargar_test.py
from main import app, db
from models import Usuario

def recargar_a_todos():
    with app.app_context():
        usuarios = Usuario.query.all()
        for u in usuarios:
            u.saldo = 5000.0  # El saldo que quieras para pruebas
            print(f"✅ Saldo de {u.username} actualizado a 5000.0")
        db.session.commit()

if __name__ == "__main__":
    recargar_a_todos()