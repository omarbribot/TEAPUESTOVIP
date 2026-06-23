import requests

# Esta prueba solo verifica si el servidor responde
try:
    res = requests.get("http://127.0.0.1:5000/")
    print(f"✅ Conexión exitosa. El servidor responde: Código {res.status_code}")
except Exception as e:
    print(f"❌ No pude conectar: {e}")