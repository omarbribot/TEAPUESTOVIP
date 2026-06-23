from main import app, db, ApuestaAnimalito, Usuario
import os

print(f"Ruta de la base de datos: {app.config['SQLALCHEMY_DATABASE_URI']}")

with app.app_context():
    todas = ApuestaAnimalito.query.all()
    print(f"Total de apuestas encontradas en la tabla: {len(todas)}")
    
    for ap in todas[-5:]: # Veamos las últimas 5
        print(f"--- Apuesta {ap.id} ---")
        print(f"Usuario ID: {ap.usuario_id}")
        print(f"Animal Apostado: '{ap.animal_elegido}'")
        print(f"Estado: {ap.estado}")