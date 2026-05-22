from datetime import datetime, timedelta
from main import app, db, Sorteo, Configuracion

with app.app_context():
    # 1. Verificar el switch en la base de datos
    config = Configuracion.query.first()
    print(f"-> Estado del Piloto Automático en BD: {config.piloto_automatico if config else 'No encontrado'}")
    
    print("-> Iniciando creación forzada de la parrilla 'Con Furia'...")

    # 2. Calcular la fecha de mañana
    hoy = datetime.now()
    manana = hoy + timedelta(days=1)
    fecha_manana_str = manana.strftime('%Y-%m-%d')

    # 3. Tu parrilla de 11 sorteos
    horas_sorteos = [
        '09:00', '10:00', '11:00', '12:00', 
        '13:00', '14:00', '15:00', '16:00', 
        '17:00', '18:00', '19:00'
    ]

    sorteos_creados = 0

    # 4. Insertar los sorteos
    for hora in horas_sorteos:
        fecha_hora_combinada = datetime.strptime(f"{fecha_manana_str} {hora}", "%Y-%m-%d %H:%M")
        existe = Sorteo.query.filter_by(horario=fecha_hora_combinada).first()

        if not existe:
            nuevo_sorteo = Sorteo(horario=fecha_hora_combinada, estado='PROGRAMADO')
            db.session.add(nuevo_sorteo)
            sorteos_creados += 1

    if sorteos_creados > 0:
        db.session.commit()
        print(f"✅ ¡Éxito total! Se programaron {sorteos_creados} sorteos automáticos para mañana ({fecha_manana_str}).")
    else:
        print(f"⚠️ La parrilla para el día {fecha_manana_str} ya estaba completa.")

    # 5. Verificar cuántos quedan en total en la BD
    total = Sorteo.query.filter_by(estado='PROGRAMADO').count()
    print(f"-> Sorteos totales programados en la BD actualmente: {total}")