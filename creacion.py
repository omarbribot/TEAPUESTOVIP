from main import app, db
from models import Configuracion

with app.app_context():
    # Esto creará SOLO las tablas que no existen. 
    # Como 'User' ya existe, no la tocará.
    db.create_all()
    
    # Verificamos si ya existe una fila de configuración, si no, la creamos
    if not Configuracion.query.first():
        nueva_config = Configuracion(
            animalitos_min=1.0, 
            animalitos_max=500.0,
            mercados_min=10.0,
            mercados_max=2000.0
        )
        db.session.add(nueva_config)
        db.session.commit()
        print("¡Tabla de configuración creada y cargada con éxito!")
    else:
        print("La tabla ya existe y tiene datos.")