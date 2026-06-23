import os
from main import app, db # Importamos app y db desde tu main.py

def limpiar_datos_prueba():
    with app.app_context():
        # Lista de tablas que quieres limpiar, usando los nombres de clase
        # Si prefieres limpiar todas, podemos hacerlo dinámicamente:
        
        tablas_a_limpiar = [
            'ApuestaMercado',
            'ApuestaAnimalito',
            'Movimiento', # Asegúrate que este sea el nombre real
            'SesionCaja',
            'Sorteo',
            'Mercado'
        ]
        
        print("⚠️ Iniciando limpieza profunda de datos financieros...")
        
        try:
            # 1. Borrar datos de tablas transaccionales
            # (El orden importa por las llaves foráneas)
            for tabla_nombre in tablas_a_limpiar:
                # Obtenemos la clase del modelo
                modelo = next((cls for cls in db.Model.__subclasses__() if cls.__name__ == tabla_nombre), None)
                if modelo:
                    db.session.query(modelo).delete()
                    print(f"🗑️ Tabla {tabla_nombre} limpiada.")
            
            # 2. Resetear saldos de usuarios (sin borrarlos)
            from models import Usuario
            db.session.query(Usuario).update({"saldo": 5000.0})
            print("💰 Saldos de usuarios iniciados en a 5000.")
            
            # 3. Resetear configuración
            from models import Configuracion
            config = Configuracion.query.first()
            if config:
                config.tasa_dolar_dia = 0.0
                config.piloto_automatico = False
            
            db.session.commit()
            print("✅ Limpieza completada con éxito. Usuarios intactos.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error crítico al limpiar: {e}")

if __name__ == "__main__":
    limpiar_datos_prueba()