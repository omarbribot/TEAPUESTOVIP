import requests
import random
import time
from constantes import TOKEN_API_SEGURO, URL_BASE, ANIMALITOS

# Lista de IDs de usuarios que tienen saldo
LISTA_USUARIOS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

def ejecutar_inyeccion(num_apuestas=20):
    endpoint = f"{URL_BASE}/apostar_animalito"
    headers = {"Authorization": f"Bearer {TOKEN_API_SEGURO}"}
    
    print(f"--- Iniciando inyección aleatoria de {num_apuestas} apuestas ---")
    
    for i in range(num_apuestas):
        # 1. Selección aleatoria de datos
        user_id_random = random.choice(LISTA_USUARIOS)
        monto_random = round(random.uniform(50.0, 200.0), 2)
        
        # 2. Selección de animal: Enviamos SOLO la llave (código)
        # Esto envía "0", "9", "36", etc., según tu diccionario ANIMALITOS
        num_random = random.choice(list(ANIMALITOS.keys()))
        
        # Datos limpios: el servidor se encargará de traducir el código al nombre
        datos = {
            "user_id": user_id_random,
            "monto": monto_random,
            "sorteo_id": 3, 
            "animal": num_random 
        }
        
        try:
            response = requests.post(endpoint, json=datos, headers=headers)
            resultado = response.json()
            
            status = response.status_code
            msg = resultado.get('message', 'Sin mensaje')
            # Imprimimos el código enviado para auditoría
            print(f"[{i+1}] Usuario {user_id_random} -> Código {num_random} ({monto_random} Bs): {status} - {msg}")
            
        except Exception as e:
            print(f"Error en inyección: {e}")
        
        time.sleep(random.uniform(0.3, 0.7))

if __name__ == "__main__":
    ejecutar_inyeccion(50)