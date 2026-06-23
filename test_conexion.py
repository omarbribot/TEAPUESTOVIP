from main import app, db, ApuestaAnimalito

with app.app_context():
    # Buscamos las últimas 5 apuestas
    apuestas = ApuestaAnimalito.query.order_by(ApuestaAnimalito.id.desc()).limit(5).all()
    print("\n--- ANALIZANDO ÚLTIMAS APUESTAS ---")
    for ap in apuestas:
        print(f"ID: {ap.id} | Animal en DB: '{ap.animal_elegido}' | Estado: {ap.estado}")