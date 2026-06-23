import requests
import random
import time
from constantes import TOKEN_API_SEGURO, URL_BASE, ANIMALITOS

# Lista de IDs de usuarios que tienen saldo
LISTA_USUARIOS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

def ejecutar_inyeccion(num_apuestas=15):
    endpoint = f"{URL_BASE}/apostar_animalito"
    headers = {"Authorization": f"Bearer {TOKEN_API_SEGURO}"}
    
    print(f"--- Iniciando inyección aleatoria de {num_apuestas} apuestas ---")
    
    for i in range(num_apuestas):
        # 1. Selección aleatoria de datos
        user_id_random = random.choice(LISTA_USUARIOS)
        monto_random = round(random.uniform(50.0, 200.0), 2)
        
        # 2. Selección de animal
        num_random = random.choice(list(ANIMALITOS.keys()))
        nombre_animal = ANIMALITOS[num_random]
        
        # Formateo estricto para coincidir con el sistema manual
        # Usamos zfill(2) para asegurar 00, 01, ..., 36
        animal_formateado = f"{num_random.zfill(2)} - {nombre_animal}"
        
        datos = {
            "user_id": user_id_random,
            "monto": monto_random,
            "sorteo_id": 13, # Asegúrate de que este ID sea el sorteo activo
            "animal": animal_formateado 
        }
        
        try:
            response = requests.post(endpoint, json=datos, headers=headers)
            resultado = response.json()
            
            status = response.status_code
            msg = resultado.get('message', 'Sin mensaje')
            print(f"[{i+1}] Usuario {user_id_random} -> {animal_formateado} ({monto_random} Bs): {status} - {msg}")
            
        except Exception as e:
            print(f"Error en inyección: {e}")
        
        time.sleep(random.uniform(0.3, 0.7))

if __name__ == "__main__":
    ejecutar_inyeccion(500)