import os
import zipfile
from datetime import datetime

def realizar_respaldo():
    nombre_proyecto = "TEAPUESTOVIP_BACKUP"
    carpeta_destino = "respaldos"
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archivo_zip = os.path.join(carpeta_destino, f"{nombre_proyecto}_{fecha}.zip")
    
    # Crear carpeta de respaldos si no existe
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)

    # Carpetas que NO queremos respaldar (para que no pese GB)
    excluir = {carpeta_destino, 'venv', '__pycache__', '.git', '.vscode', '.idea'}

    print(f"Iniciando respaldo en: {archivo_zip}...")

    try:
        with zipfile.ZipFile(archivo_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for raiz, carpetas, archivos in os.walk(os.getcwd()):
                # Filtrar carpetas excluidas
                carpetas[:] = [d for d in carpetas if d not in excluir]
                
                for archivo in archivos:
                    # No respaldar el propio script de backup ni el archivo zip que estamos creando
                    if archivo == 'backup.py' or archivo.endswith('.zip'):
                        continue
                        
                    ruta_completa = os.path.join(raiz, archivo)
                    ruta_relativa = os.path.relpath(ruta_completa, os.getcwd())
                    zipf.write(ruta_completa, ruta_relativa)
        
        print(f"✅ ¡Respaldo completado con éxito!")
        
    except Exception as e:
        print(f"❌ Error durante el respaldo: {e}")

if __name__ == "__main__":
    realizar_respaldo()