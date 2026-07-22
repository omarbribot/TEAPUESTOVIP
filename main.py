from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_wtf.csrf import CSRFProtect
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from flask_migrate import Migrate
from sqlalchemy import func
from functools import wraps
from consultas import consultas_bp
from pathlib import Path
from dotenv import load_dotenv  
import os
import random
import uuid
import time
import requests
import importlib
import constantes
from constantes import ANIMALITOS, ICONOS_ANIMALITOS, TOKEN_API_SEGURO
from flask_apscheduler import APScheduler
import pytz
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)
# Zona horaria oficial de Venezuela
TZ_VENEZUELA = pytz.timezone('America/Caracas')

# Función helper para obtener siempre la hora real de Venezuela sin zona horaria adjunta (naive)
# Esto garantiza que SQLAlchemy y SQLite la comparen perfectamente en las consultas
def get_hora_ve():
    # 1. Obtenemos la hora directamente
    hora_ve = datetime.now(TZ_VENEZUELA).replace(tzinfo=None)
    
    # 2. Imprimimos para verificar (Esto solo sale en tu consola, no afecta al programa)
    # print(f"--- [DEBUG HORA] Hora real tomada por el sistema: {hora_ve} ---")
    
    # 3. Retornamos exactamente lo mismo que tenías antes
    return hora_ve
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Verificamos si viene por navegador (login activo)
        if current_user and current_user.is_authenticated:
            return f(*args, **kwargs)
        
        # 2. Verificamos si viene el token de API para inyecciones
        token = request.headers.get('Authorization')
        if token == f"Bearer {TOKEN_API_SEGURO}":
            return f(*args, **kwargs)
        
        # 3. Si no hay nada, acceso denegado
        return jsonify({'status': 'error', 'message': 'Acceso no autorizado'}), 403
    return decorated_function
# 1. CONFIGURACIÓN INICIAL
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'un_fallback_local_muy_largo_y_complejo_xyz_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'teapuesto.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.register_blueprint(consultas_bp)
# --- CONFIGURACIÓN DE CORREO (SMTP) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False  # Importante: SSL en False al usar TLS
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'inversionesomarbri@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('TEAPUESTOVIP', os.environ.get('MAIL_USERNAME', 'inversionesomarbri@gmail.com'))

mail = Mail(app)

# Serializador para generar tokens seguros con fecha de expiración
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
# 2. IMPORTAMOS DB Y LOS MODELOS
# ◄ MODIFICACIÓN: Incluimos SesionCaja
from models import db, Usuario, Sorteo, Mercado, ApuestaMercado, ApuestaAnimalito, Movimiento, Configuracion, SesionCaja
# 3. INICIALIZAMOS COMPONENTES
app.config['SCHEDULER_TIMEZONE'] = "America/Caracas"
app.config['SCHEDULER_API_ENABLED'] = True
db.init_app(app)
migrate = Migrate(app, db)
scheduler = APScheduler()
#scheduler.timezone = TZ_VENEZUELA
scheduler.init_app(app)
scheduler.start()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

def actualizar_tasa_dolar():
    """
    Actualiza la tasa del dólar en la base de datos usando dos fuentes de respaldo.
    """
    tasa_obtenida = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Intentar con la Opción 1 (ER-API)
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            datos = response.json()
            tasa_ves = datos.get("rates", {}).get("VES")
            if tasa_ves:
                tasa_obtenida = round(float(tasa_ves), 2)
                print(f"✅ Tasa obtenida vía API Global: {tasa_obtenida}")
    except Exception as e:
        print(f"⚠️ Error en API Global: {e}")

    # Si la opción 1 falló, intentar con el respaldo (pydolarvenezuela)
    if not tasa_obtenida:
        try:
            url_respaldo = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar?page=bcv"
            response = requests.get(url_respaldo, headers=headers, timeout=5)
            if response.status_code == 200:
                datos = response.json()
                # Ajuste según la estructura real de respuesta que tiene esa API
                price = datos.get('monedas', {}).get('usd', {}).get('price')
                if price:
                    tasa_obtenida = float(price)
                    print(f"✅ Tasa obtenida vía Respaldo: {tasa_obtenida}")
        except Exception as e:
            print(f"⚠️ Error en API de Respaldo: {e}")

    # Si conseguimos una tasa válida, guardarla en BD
    if tasa_obtenida:
        with app.app_context():
            config = Configuracion.query.first()
            if config:
                config.tasa_dolar_dia = tasa_obtenida
                db.session.commit()
    else:
        print("❌ Fallaron todas las fuentes para obtener la tasa del dólar.")
from flask import request, abort # Asegúrate de importar abort

@app.route('/ejecutar-sorteo-secreto-xyz789')
def ejecucion_forzada_externa():
    # Usamos la constante importada
    token_recibido = request.args.get('token')
    
    if token_recibido != TOKEN_API_SEGURO:
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        ejecutar_programacion_parrilla(datetime.now() + timedelta(days=1))
        return jsonify({"status": "success", "message": "Parrilla de mañana generada"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.context_processor
def utility_processor():
    def obtener_icono(numero):
        num_str = str(numero)
        return ICONOS_ANIMALITOS.get(num_str, "fa-paw")
    return dict(obtener_icono=obtener_icono)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# --- LÓGICA DE SORTEO AUTOMÁTICO (CONSOLIDADA) ---
def ejecutar_giro_animalito(sorteo_id):
    with app.app_context():
        # --- NUEVA SEGURIDAD: SI EL PILOTO ESTÁ APAGADO, NO HACER NADA ---
        config = Configuracion.query.first()
        if not config or not config.piloto_automatico:
            print(f"⚠️ [Piloto] Sorteo {sorteo_id} cancelado por estar DESACTIVADO.")
            return
        # -----------------------------------------------------------------
        
        sorteo = db.session.get(Sorteo, sorteo_id)
        if not sorteo or sorteo.estado.upper() == 'FINALIZADO':
            return

        # 1. Elegir ganador
        numero_ganador = random.choice(list(ANIMALITOS.keys()))
        nombre_ganador = ANIMALITOS[numero_ganador]

        sorteo.numero = numero_ganador
        sorteo.nombre_animal = nombre_ganador
        sorteo.estado = 'FINALIZADO'

        # 2. Lógica de condiciones especiales (Par/Impar)
        val_num = int(numero_ganador)
        es_par = (val_num % 2 == 0) and (val_num != 0) # El 0 no es par ni impar
        es_impar = (val_num % 2 != 0)

        # 3. Procesar todas las apuestas pendientes de este sorteo
        apuestas = ApuestaAnimalito.query.filter_by(sorteo_id=sorteo_id, estado='PENDIENTE').all()

        for ap in apuestas:
            gano = False
            cuota = 0

           # Esto funcionará tanto si el usuario eligió "09" como si eligió "09 - ÁGUILA"
            animal_limpio = str(ap.animal_elegido).split()[0].zfill(2)
            resultado_limpio = str(numero_ganador).zfill(2)

            if animal_limpio == resultado_limpio:
                gano, cuota = True, 30
            elif ap.animal_elegido == 'PAR' and es_par:
                gano, cuota = True, 1.95
            elif ap.animal_elegido == 'IMPAR' and es_impar:
                gano, cuota = True, 1.95
            if gano:
                premio = round(ap.monto * cuota, 2)
                ap.estado = 'GANADA'
                ap.monto_ganado = premio
                ap.usuario.saldo = round(ap.usuario.saldo + premio, 2)

                # ◄ AUDITORÍA: Registro de pago de premio (Animalitos)
                mov_premio = Movimiento(
                    user_id=ap.usuario_id,
                    tipo='PREMIO_ANIMALITO',
                    monto=premio,
                    referencia=f"PRM-A-{sorteo_id}",
                    banco_emisor='Sistema VIP',
                    estatus='Completado',
                    fecha_transaccion=get_hora_ve()
                )
                db.session.add(mov_premio)
            else:
                ap.estado = 'PERDIDA'
                ap.monto_ganado = 0

        try:
            db.session.commit()
            print(f"✅ Sorteo {sorteo_id} finalizado: {numero_ganador} ({nombre_ganador})")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al procesar sorteo {sorteo_id}: {e}")

# --- SIMULADOR DE PASARELA BANCARIA ---
def mock_api_pago_movil(telefono, cedula, banco, monto):
    time.sleep(1.5)
    return {
        "status": "success",
        "referencia_bancaria": f"RET-{uuid.uuid4().hex[:6].upper()}",
        "mensaje": "Pago Móvil enviado con éxito"
    }

# --- RUTAS DE USUARIO ---
@app.route('/')
def home():
    ahora = get_hora_ve()
    hora_limite_apuestas = ahora + timedelta(seconds=120)

    # Filtramos para traer solo sorteos que no estén FINALIZADOS Y cuyo horario sea mayor a la hora límite
    sorteos_db = Sorteo.query.filter(
        Sorteo.estado != 'FINALIZADO',
        Sorteo.horario > hora_limite_apuestas
    ).order_by(Sorteo.horario.asc()).all()

    for s in sorteos_db:
        s.hora_formateada = s.horario.strftime('%I:%M %p')
        segundos_para_el_sorteo = (s.horario - ahora).total_seconds()
        segundos_para_cierre = segundos_para_el_sorteo - 120
        s.segundos_restantes = int(segundos_para_cierre) if segundos_para_cierre > 0 else 0

    mercados_db = Mercado.query.filter(
        Mercado.estado == 'Abierto',
        (Mercado.fecha_cierre > ahora) | (Mercado.fecha_cierre == None)
    ).all()

    ultimos_resultados = Sorteo.query.filter_by(estado='FINALIZADO')\
                                     .order_by(Sorteo.horario.desc())\
                                     .limit(15).all()

    es_admin = (current_user.is_authenticated and current_user.username == 'omarbri')

    for m in mercados_db:
        total_m = m.total_si + m.total_no
        m.p_si = round((m.total_si / total_m * 100), 1) if total_m > 0 else 50
        m.p_no = round((m.total_no / total_m * 100), 1) if total_m > 0 else 50

    mis_apuestas = []
    if current_user.is_authenticated:
        mis_apuestas = ApuestaMercado.query.filter_by(usuario_id=current_user.id, estado='PENDIENTE').all()

    return render_template('index.html',
                           mercados=mercados_db,
                           sorteos_activos=sorteos_db,
                           soy_admin=es_admin,
                           apuestas_usuario=mis_apuestas,
                           animalitos_dict=ANIMALITOS,
                           resultados=ultimos_resultados)



# ==========================================
# 🎰 RUTA DE APUESTA ANIMALITO BLINDADA
# ==========================================
@app.route('/apostar_animalito', methods=['POST'])
@csrf.exempt
@login_required
def apostar_animalito():
    data = request.get_json()
    sorteo_id = data.get('sorteo_id')
    animal_elegido = data.get('animal')
    
    try:
        monto = float(data.get('monto', 0))
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Monto no válido'}), 400
    
    if monto <= 0:
        return jsonify({'status': 'error', 'message': 'Monto inválido'}), 400
    
    try:
        # BLOQUEO DE FILA: Evita la compra múltiple concurrente (Race Condition)
        usuario = Usuario.query.with_for_update().get(current_user.id)
        
        if usuario.saldo < monto:
            return jsonify({'status': 'error', 'message': 'Saldo insuficiente'}), 400
            
        sorteo = db.session.get(Sorteo, sorteo_id)
        if sorteo:
            ahora = get_hora_ve()
            segundos_restantes = (sorteo.horario - ahora).total_seconds()
            if segundos_restantes < 120:
                return jsonify({'status': 'error', 'message': 'Sorteo cerrado. Tolerancia de 2 minutos vencida.'}), 400
        
        if not sorteo or sorteo.estado.upper() not in ['PENDIENTE', 'PROGRAMADO']:
            return jsonify({'status': 'error', 'message': 'Sorteo no disponible o ya cerrado'}), 400

        # Modificación atómica
        usuario.saldo = round(usuario.saldo - monto, 2)
        
        nueva_apuesta = ApuestaAnimalito(
            usuario_id=usuario.id,
            sorteo_id=sorteo_id,
            animal_elegido=str(animal_elegido).upper(),
            monto=monto,
            estado='PENDIENTE'
        )
        db.session.add(nueva_apuesta)

        mov_compra_a = Movimiento(
            user_id=usuario.id,
            tipo='Apuesta Animalito',
            monto=-monto,
            referencia=f"APS-A-{sorteo_id}-{animal_elegido}",
            banco_emisor='Saldo Interno',
            estatus='Completado',
            fecha_transaccion=get_hora_ve()
        )
        db.session.add(mov_compra_a)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Apuesta al {animal_elegido} procesada',
            'nuevo_saldo': f"{usuario.saldo:,.2f}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Error interno al procesar apuesta.'}), 500

# ==========================================
# 📊 RUTA DE APUESTA MERCADO BLINDADA
# ==========================================
@app.route('/apostar_mercado', methods=['POST'])
@csrf.exempt
@login_required
def apostar_mercado():
    data = request.get_json()
    mercado_id = data.get('mercado_id')
    opcion = data.get('opcion')
    
    try:
        monto = float(data.get('monto', 0))
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Monto no válido'}), 400

    try:
        # BLOQUEO DE FILA
        usuario = Usuario.query.with_for_update().get(current_user.id)
        
        config = Configuracion.query.first()
        if config:
            if monto < config.mercados_min:
                return jsonify({'status': 'error', 'message': f'Monto mínimo es {config.mercados_min}'}), 400
            if monto > config.mercados_max:
                return jsonify({'status': 'error', 'message': f'Monto máximo es {config.mercados_max}'}), 400

        if monto <= 0 or usuario.saldo < monto:
            return jsonify({'status': 'error', 'message': 'Saldo insuficiente o monto inválido'}), 400
        
        mercado = db.session.get(Mercado, mercado_id)
        if not mercado or mercado.estado != 'Abierto':
            return jsonify({'status': 'error', 'message': 'Mercado cerrado'}), 400

        # Modificación atómica
        usuario.saldo = round(usuario.saldo - monto, 2)
        
        nueva_apuesta = ApuestaMercado(
            usuario_id=usuario.id,
            mercado_id=mercado_id,
            opcion_elegida=opcion,
            monto=monto,
            estado='PENDIENTE'
        )
        db.session.add(nueva_apuesta)

        mov_compra_m = Movimiento(
            user_id=usuario.id,
            tipo='Apuesta Mercado',
            monto=-monto,
            referencia=f"APS-M-{mercado_id}",
            banco_emisor='Saldo Interno',
            estatus='Completado',
            fecha_transaccion=get_hora_ve()
        )
        db.session.add(mov_compra_m)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': '¡Apuesta procesada!',
            'nuevo_saldo': f"{usuario.saldo:,.2f}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Error al procesar la predicción.'}), 500

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter((Usuario.username == identificador) | (Usuario.email == identificador)).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Usuario/Correo o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        cedula = request.form.get('cedula')
        username = request.form.get('username')
        email = request.form.get('email').lower().strip()
        telefono = request.form.get('telefono')
        password = request.form.get('password')

        user_existente = Usuario.query.filter((Usuario.username == username) | (Usuario.email == email) | (Usuario.cedula == cedula)).first()
        if user_existente:
            flash("El usuario, correo o cédula ya están registrados.")
            return redirect(url_for('registro'))

        nuevo_usuario = Usuario(nombre_completo=nombre, cedula=cedula, username=username, email=email, telefono=telefono, saldo=0.0)
        nuevo_usuario.set_password(password)
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash("Usuario creado con éxito.")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("Error al registrar el usuario.")
    return render_template('registro.html')

@app.route('/retirar')
@login_required
def retirar():
    return render_template('retirar.html')

@app.route('/mi_historial')
@login_required
def mi_historial():
    apuestas_animalitos = ApuestaAnimalito.query.filter_by(usuario_id=current_user.id).order_by(ApuestaAnimalito.fecha.desc()).all()
    apuestas_mercados = ApuestaMercado.query.filter_by(usuario_id=current_user.id).order_by(ApuestaMercado.fecha.desc()).all()
    return render_template('historial_personal.html', animalitos=apuestas_animalitos, mercados=apuestas_mercados, animalitos_dict=ANIMALITOS)

# 🔥 NUEVA RUTA: Historial de transacciones/movimientos para el cliente
@app.route('/mis_transacciones')
@login_required
def mis_transacciones():
    movimientos_usuario = Movimiento.query.filter_by(user_id=current_user.id).order_by(Movimiento.id.desc()).all()
    return render_template('transacciones.html', movimientos=movimientos_usuario)

# --- RUTAS DE ADMINISTRACIÓN ---
@app.route('/admin')
@login_required
def admin():
    if current_user.username != 'omarbri':
        return "No autorizado", 403

    page = request.args.get('page', 1, type=int)
    paginacion_usuarios = Usuario.query.paginate(page=page, per_page=10, error_out=False)

    page_sorteos = request.args.get('page_sorteos', 1, type=int)
    paginacion_sorteos = Sorteo.query.order_by(Sorteo.horario.desc()).paginate(page=page_sorteos, per_page=10, error_out=False)

    page_historial = request.args.get('page_historial', 1, type=int)
    paginacion_historial = Mercado.query.filter_by(estado='Cerrado')\
                                         .order_by(Mercado.fecha_cierre.desc())\
                                         .paginate(page=page_historial, per_page=10, error_out=False)

    count_animalitos = ApuestaAnimalito.query.count()
    count_mercados = ApuestaMercado.query.count()

    mercados_db = Mercado.query.filter_by(estado='Abierto').all()
    mercados_stats = []
    for m in mercados_db:
        total = m.total_si + m.total_no
        mercados_stats.append({
            'pregunta': m.pregunta, 'fecha_cierre': m.fecha_cierre,
            'p_si': round((m.total_si / total * 100), 1) if total > 0 else 50,
            'p_no': round((m.total_no / total * 100), 1) if total > 0 else 50,
            'total': total, 'total_si': m.total_si, 'total_no': m.total_no,
            'cuota_si': m.cuota_si, 'cuota_no': m.cuota_no
        })

    total_apostado = (db.session.query(func.sum(ApuestaAnimalito.monto)).scalar() or 0) + (db.session.query(func.sum(ApuestaMercado.monto)).scalar() or 0)
    total_premios = (db.session.query(func.sum(ApuestaAnimalito.monto_ganado)).scalar() or 0) + (db.session.query(func.sum(ApuestaMercado.monto_ganado)).scalar() or 0)

    config = Configuracion.query.first()
    if not config:
        config = Configuracion(animalitos_min=1.0, animalitos_max=500.0, mercados_min=5.0, mercados_max=1000.0)
        db.session.add(config)
        db.session.commit()

    # ◄ NUEVA LÓGICA DE CONTROL DE CAJA Y ALERTA CRÍTICA (40%)
    alerta_critica = False
    if config.fondo_semilla_optimo > 0:
        if config.caja_real_disponible < (config.fondo_semilla_optimo * 0.40):
            alerta_critica = True

    # Obtenemos el historial de las últimas 10 sesiones de caja para la auditoría visual
    sesiones_caja_historico = SesionCaja.query.order_by(SesionCaja.fecha_apertura.desc()).limit(10).all()

    return render_template('admin.html',
                           sorteos=paginacion_sorteos.items,
                           paginacion_sorteos=paginacion_sorteos,
                           usuarios=paginacion_usuarios.items,
                           paginacion=paginacion_usuarios,
                           mercados_stats=mercados_stats,
                           mercados_para_resolver=mercados_db,
                           mercados_historial=paginacion_historial.items,
                           paginacion_historial=paginacion_historial,
                           ganancia_casa=total_apostado - total_premios,
                           total_apuestas=count_animalitos + count_mercados,
                           config=config,
                           alerta_critica=alerta_critica,
                           sesiones_caja=sesiones_caja_historico,
                           now=datetime.now())

@app.route('/programar_sorteo', methods=['POST'])
@login_required
def programar_sorteo():
    if current_user.username != 'omarbri': return "No autorizado", 403
    fecha_dt = datetime.strptime(request.form.get('fecha_hora'), '%Y-%m-%dT%H:%M')
    nuevo_sorteo = Sorteo(horario=fecha_dt, estado='PROGRAMADO')
    db.session.add(nuevo_sorteo)
    db.session.commit()
    scheduler.add_job(id=f'sorteo_{nuevo_sorteo.id}', func=ejecutar_giro_animalito, trigger='date', run_date=fecha_dt, args=[nuevo_sorteo.id])
    flash("Sorteo programado")
    return redirect(url_for('admin'))

@app.route('/resolver_mercado/<int:id>/<string:resultado>', methods=['POST'])
@login_required
def resolver_mercado(id, resultado):
    if current_user.username != 'omarbri': return "No autorizado", 403
    mercado = Mercado.query.get_or_404(id)
    try:
        mercado.resultado_final = resultado
        mercado.estado = 'Cerrado'
        cuota_final = mercado.cuota_si if resultado == 'SI' else mercado.cuota_no
        apuestas = ApuestaMercado.query.filter_by(mercado_id=id).all()
        for ap in apuestas:
            if ap.opcion_elegida == resultado:
                premio = ap.monto * cuota_final
                ap.monto_ganado = premio
                ap.estado = 'GANADA'
                ap.usuario.saldo = round(ap.usuario.saldo + premio, 2)

                # ◄ AUDITORÍA: Registro de pago de premio (Mercados)
                mov_premio_m = Movimiento(
                    user_id=ap.usuario_id,
                    tipo='Premio Mercado',
                    monto=premio,
                    referencia=f"PRM-M-{id}",
                    banco_emisor='Sistema VIP',
                    estatus='Completado',
                    fecha_transaccion=get_hora_ve()
                )
                db.session.add(mov_premio_m)
            else:
                ap.estado = 'PERDIDA'

        admin_user = Usuario.query.filter_by(username='omarbri').first()
        if admin_user: admin_user.saldo = round(admin_user.saldo + mercado.comision_casa, 2)
        db.session.commit()
        flash("Mercado resuelto")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}")
    return redirect(url_for('admin'))

@app.route('/recargar_saldo', methods=['POST'])
@login_required
def recargar_saldo():
    # 1. Validación de seguridad estricta del Administrador
    if current_user.username != 'omarbri': 
        return "No autorizado", 403

    user_id = request.form.get('user_id')
    try:
        monto = float(request.form.get('monto', 0))
    except (ValueError, TypeError):
        return "Monto inválido", 400

    if monto <= 0:
        return "El monto a recargar debe ser mayor a cero", 400

    # 2. Bloque de Transacción Atómica
    try:
        # 'with_for_update()' bloquea la fila del usuario en la BD. 
        # Nadie puede modificar su saldo desde otra ruta hasta que este commit termine.
        usuario = Usuario.query.with_for_update().get(user_id)
        
        if not usuario:
            return "Usuario no encontrado", 404

        # Modificación del saldo segura
        usuario.saldo = round(usuario.saldo + monto, 2)

        # Registro estricto de Auditoría financiera
        mov_manual = Movimiento(
            user_id=usuario.id,
            tipo='Recarga Manual',
            monto=monto,
            referencia=f"ADM-REC-{uuid.uuid4().hex[:4].upper()}",
            banco_emisor='Admin Panel',
            estatus='Completado',
            fecha_transaccion=get_hora_ve()
        )
        
        db.session.add(mov_manual)
        
        # Al hacer commit se guardan AMBAS cosas al mismo tiempo. Si una falla, no se guarda ninguna.
        db.session.commit()
        print(f">>> [FINANZAS] Recarga exitosa. Usuario ID {usuario.id} +{monto} USD.")
        
    except Exception as e:
        db.session.rollback() # Si algo falla en el camino, deshace todo y el dinero queda intacto
        print(f"!!! [CRÍTICO] Falló la recarga del usuario {user_id}: {e}")
        return "Error interno al procesar la transacción. Operación cancelada de forma segura.", 500

    return redirect(url_for('admin'))

# --- WEBHOOK Y RETIROS ---
@app.route('/webhook/pagos', methods=['POST'])
@csrf.exempt
def webhook_pagos():
    data = request.get_json()
    if data.get('token') != "VIP_TOKEN_2026_TEST": 
        return jsonify({"status": "error"}), 401
        
    usuario = db.session.get(Usuario, data.get('user_id'))
    if usuario:
        try:
            monto = round(float(data.get('monto')), 2)
            usuario.saldo = round(usuario.saldo + monto, 2)
            
            # ◄ NUEVA LÓGICA DE CONVERSIÓN DE FECHA A DATETIME
            fecha_final = data.get('fecha_personalizada')
            if fecha_final:
                try:
                    # Si el simulador envía texto "DD/MM/YYYY", lo transformamos a objeto datetime
                    fecha_obj = datetime.strptime(fecha_final, "%d/%m/%Y")
                except ValueError:
                    # Si por alguna razón el formato no coincide, usamos la hora de Venezuela como respaldo
                    fecha_obj = get_hora_ve()
            else:
                # Si no se envía fecha personalizada, asignamos la hora real actual de Venezuela
                fecha_obj = get_hora_ve()

            db.session.add(Movimiento(
                user_id=usuario.id, 
                tipo='Recarga', 
                monto=monto, 
                referencia=data.get('referencia'), 
                banco_emisor=data.get('banco', 'Pago Móvil'), 
                estatus='Completado', 
                fecha_transaccion=fecha_obj  # ◄ Guardamos el objeto datetime limpio
            ))
            db.session.commit()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error"}), 404
# ==========================================
# 💸 RUTA DE RETIROS BLINDADA
# ==========================================
@app.route('/solicitar_retiro_auto', methods=['POST'])
@csrf.exempt
@login_required
def solicitar_retiro_auto():
    data = request.get_json()
    try:
        monto = float(data.get('monto', 0))
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Monto inválido'}), 400

    if monto < 10:
        return jsonify({'status': 'error', 'message': 'El monto mínimo de retiro es 10 USD'}), 400

    # Iniciamos el bloque de transacción atómica estricta
    try:
        # BLOQUEO DE FILA: Nadie puede tocar este usuario hasta el db.session.commit()
        usuario = Usuario.query.with_for_update().get(current_user.id)
        
        if usuario.saldo < monto:
            return jsonify({'status': 'error', 'message': 'Saldo insuficiente'}), 400

        # 1. Primero debitamos el saldo internamente de forma segura en la BD
        usuario.saldo = round(usuario.saldo - monto, 2)
        
        # 2. Ahora que el saldo está comprometido y bloqueado, llamamos de forma segura a la API externa/Simulador
        res_banco = mock_api_pago_movil(data.get('telefono'), data.get('cedula'), data.get('banco'), monto)
        
        if res_banco.get('status') != 'success':
            raise Exception("La pasarela bancaria rechazó la transacción.")

        # 3. Registramos la auditoría del movimiento financiero
        mov_retiro = Movimiento(
            user_id=usuario.id, 
            tipo='Retiro', 
            monto=-monto, # Salida de dinero
            referencia=res_banco['referencia_bancaria'], 
            banco_emisor=data.get('banco'), 
            estatus='Completado', 
            fecha_transaccion=get_hora_ve()
        )
        db.session.add(mov_retiro)
        
        # Confirmamos la operación en la BD y liberamos el bloqueo del usuario
        db.session.commit()
        return jsonify({'status': 'success', 'nuevo_saldo': f"{usuario.saldo:,.2f}"})

    except Exception as e:
        db.session.rollback() # Si el banco falla o la BD truena, el dinero regresa intacto al usuario
        print(f"!!! [FALLO CRÍTICO RETIRO] Usuario {current_user.id}: {e}")
        return jsonify({'status': 'error', 'message': 'No se pudo procesar el retiro de forma segura.'}), 500

@scheduler.task('interval', id='revisar_pendientes', seconds=120) # Aumentado a 2 minutos
def revisar_sorteos_pasados():
    with app.app_context():
        # 1. Validación de configuración
        config = Configuracion.query.first()
        if not config or not config.piloto_automatico:
            return
        
        # 2. Consultar solo sorteos pasados pero muy cercanos (ej: hace menos de 1 hora)
        # Esto evita escanear toda la historia de sorteos si el servidor falló hace días.
        hace_una_hora = get_hora_ve() - timedelta(hours=1)
        
        pendientes = Sorteo.query.filter(
            Sorteo.horario <= get_hora_ve(), 
            Sorteo.horario >= hace_una_hora,
            Sorteo.estado != 'FINALIZADO'
        ).all()
        
        if not pendientes:
            return
        
        # 3. Procesamiento
        for s in pendientes:
            print(f"--- [INFO] Ejecutando sorteo pendiente: {s.id} ---")
            ejecutar_giro_animalito(s.id)
        
# =====================================================================
# 🚀 ROUTINE: PILOTO AUTOMÁTICO (MODULARIZADA)
# =====================================================================
def ejecutar_programacion_parrilla(fecha_destino):
    fecha_str = fecha_destino.strftime('%Y-%m-%d')
    horas_sorteos = [
        '09:00', '10:00', '11:00', '12:00',
        '13:00', '14:00', '15:00', '16:00',
        '17:00', '18:00', '19:00'
    ]
    sorteos_creados = 0

    for hora in horas_sorteos:
        fecha_hora_combinada = datetime.strptime(f"{fecha_str} {hora}", "%Y-%m-%d %H:%M")

        if fecha_hora_combinada < get_hora_ve():
            continue

        existe = Sorteo.query.filter_by(horario=fecha_hora_combinada).first()

        if not existe:
            nuevo_sorteo = Sorteo(horario=fecha_hora_combinada, estado='PROGRAMADO')
            db.session.add(nuevo_sorteo)
            sorteos_creados += 1

    if sorteos_creados > 0:
        try:
            db.session.commit()
            print(f"✅ [Piloto] ¡Éxito! Se programaron {sorteos_creados} sorteos automáticamente para el día {fecha_str}.")

            inicio_dia = datetime.strptime(f"{fecha_str} 00:00", "%Y-%m-%d %H:%M")
            sorteos_nuevos = Sorteo.query.filter(Sorteo.horario >= inicio_dia).all()
            for s in sorteos_nuevos:
                if not scheduler.get_job(f'sorteo_{s.id}'):
                    scheduler.add_job(
                        id=f'sorteo_{s.id}',
                        func=ejecutar_giro_animalito,
                        trigger='date',
                        run_date=s.horario,
                        args=[s.id]
                    )
        except Exception as e:
            db.session.rollback()
            print(f"❌ [Piloto] Error al guardar el cronograma automático: {e}")
    else:
        print(f"⚠️ [Piloto] El día {fecha_str} ya tiene su parrilla completa o las horas ya pasaron.")

@scheduler.task('cron', id='generar_cronograma_diario', hour=23, minute=0)
def generar_cronograma_diario():
    with app.app_context():
        config = Configuracion.query.first()
        if not config or not config.piloto_automatico:
            print("[Piloto] DESACTIVADO. Saltando la generación del cronograma.")
            return

        print("[Piloto] ACTIVADO. Iniciando creación de la parrilla nocturna para mañana...")
        manana = datetime.now() + timedelta(days=1)
        ejecutar_programacion_parrilla(manana.date())


# =====================================================================
# 📊 NUEVA LÓGICA CORE: CONTROL DE CAJA Y FÓRMULAS DIARIAS
# =====================================================================
def ejecutar_cierre_procesamiento_caja(monto_declarado_manual=None):
    """
    Procesa las fórmulas financieras del negocio basadas estrictamente en Bolívares (Bs)
    Fórmula: Ganancia Real Diaria = (Ventas Animalitos - Premios Animalitos) + Comisión Mercados (5%)
    """
    ahora = get_hora_ve()
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    
    config = Configuracion.query.first()
    if not config:
        return False

    # 1. Calcular Ventas del Día (Animalitos)
    ventas_animalitos = db.session.query(func.sum(ApuestaAnimalito.monto))\
        .filter(ApuestaAnimalito.fecha >= inicio_dia).scalar() or 0.0

    # 2. Calcular Premios del Día (Animalitos)
    premios_animalitos = db.session.query(func.sum(ApuestaAnimalito.monto_ganado))\
        .filter(ApuestaAnimalito.fecha >= inicio_dia, ApuestaAnimalito.estado == 'GANADA').scalar() or 0.0

    # 3. Calcular Comisión de Mercados del Día (5%)
    comision_mercados = 0.0
    mercados_cerrados_hoy = Mercado.query.filter(Mercado.fecha_cierre >= inicio_dia, Mercado.estado == 'Cerrado').all()
    for m in mercados_cerrados_hoy:
        comision_mercados += m.comision_casa

    # Aplicación de Fórmula Financiera Aprobada
    ganancia_real_diaria = (ventas_animalitos - premios_animalitos) + comision_mercados

    # Calcular monto que debería registrar el sistema basándose en la caja anterior y el flujo neto
    monto_apertura_hoy = config.caja_real_disponible
    monto_calculado_sistema = monto_apertura_hoy + ganancia_real_diaria

    # Definir el monto de cierre real (Si es automático por cron toma el del sistema, si es manual usa el del admin)
    monto_real_final = monto_declarado_manual if monto_declarado_manual is not None else monto_calculado_sistema
    discrepancia_calculada = monto_real_final - monto_calculado_sistema

    # Determinar estado de la auditoría
    estado_sesion = 'Cerrada'
    if discrepancia_calculada < 0:
        estado_sesion = 'Cerrada con Déficit'
    elif discrepancia_calculada > 0:
        estado_sesion = 'Cerrada con Superávit'

    # Guardar histórico de auditoría en SesionCaja
    nueva_sesion = SesionCaja(
        fecha_apertura=inicio_dia,
        fecha_cierre=ahora,
        monto_apertura_bs=monto_apertura_hoy,
        monto_cierre_sistema=monto_calculado_sistema,
        monto_cierre_real=monto_real_final,
        discrepancy=discrepancia_calculada,
        estado=estado_sesion
    )
    db.session.add(nueva_sesion)

    # Regla de Negocio 1 (Fondo Semilla Intocable)
    if monto_real_final >= config.fondo_semilla_optimo:
        # Si hay ganancia o está cuadrado exacto, el excedente va a utilidades y la caja abre limpia con el fondo óptimo
        config.caja_real_disponible = config.fondo_semilla_optimo
    else:
        # Si hay pérdida y no llega al fondo óptimo, abre disminuida reflejando el déficit directo
        config.caja_real_disponible = monto_real_final

    try:
        db.session.commit()
        print(f"📊 [Caja] Sesión Guardada de forma exitosa. Estado: {estado_sesion}, Caja operativa: {config.caja_real_disponible} Bs.")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ [Caja] Error al procesar el cierre financiero: {e}")
        return False

# Regla 3: Cierre Híbrido Automático a las 11:59 PM vía Flask-APScheduler
# Reemplaza tu tarea actual por esta versión optimizada
@scheduler.task('cron', id='cierre_automatico_caja_cron', hour=23, minute=59)
def cierre_automatico_caja_cron():
    with app.app_context():
        # Usamos explícitamente nuestra función helper que garantiza hora Vzla
        hora_cierre = get_hora_ve() 
        print(f"🕒 [Caja] Ejecutando cierre automático. Hora sistema Vzla: {hora_cierre}")
        
        # Pasamos la hora actual para que el cálculo de rango sea preciso
        ejecutar_cierre_procesamiento_caja()
@scheduler.task('cron', id='actualizar_tasa_cron', hour=8, minute=30)
def cron_actualizar_tasa():
    
    actualizar_tasa_dolar()
# --- NUEVAS RUTAS DE CAJA (PANEL ADMINISTRADOR) ---
@app.route('/admin/cierre_manual_caja', methods=['POST'])
@login_required
def cierre_manual_caja():
    if current_user.username != 'omarbri': 
        return "No autorizado", 403
    
    try:
        monto_real = float(request.form.get('monto_cierre_real', 0.0))
    except (ValueError, TypeError):
        flash("Monto real declarado no es válido.")
        return redirect(url_for('admin'))

    exito = ejecutar_cierre_procesamiento_caja(monto_declarado_manual=monto_real)
    if exito:
        flash("¡Cierre de caja manual procesado y auditado con éxito!")
    else:
        flash("Ocurrió un error interno al guardar la sesión de caja.")
    return redirect(url_for('admin'))

@app.route('/admin/actualizar_parametros_caja', methods=['POST'])
@login_required
def actualizar_parametros_caja():
    if current_user.username != 'omarbri': 
        return "No autorizado", 403

    config = Configuracion.query.first()
    if config:
        config.tasa_dolar_dia = float(request.form.get('tasa_dolar', config.tasa_dolar_dia))
        config.fondo_semilla_optimo = float(request.form.get('fondo_semilla', config.fondo_semilla_optimo))
        config.caja_real_disponible = float(request.form.get('caja_disponible', config.caja_real_disponible))
        db.session.commit()
        flash("Parámetros de caja y tasas bimoneda actualizados.")
    return redirect(url_for('admin'))


from constantes import ANIMALITOS # Asegúrate de tener esto

@app.route('/detalle_sorteo_animalito/<int:sorteo_id>')
@login_required
def detalle_sorteo_animalito(sorteo_id):
    if current_user.username != 'omarbri':
        return jsonify({'status': 'error', 'message': 'Acceso denegado'}), 403
    apuestas = ApuestaAnimalito.query.filter_by(sorteo_id=sorteo_id).all()
    resultado = []
    for ap in apuestas:
        # Si la apuesta es PAR o IMPAR, el nombre es la condición misma de manera limpia
        if str(ap.animal_elegido).upper() in ['PAR', 'IMPAR']:
            nombre_renderizado = str(ap.animal_elegido).upper()
        else:
            nombre_renderizado = ANIMALITOS.get(str(ap.animal_elegido), 'Animalito')

        resultado.append({
            'username': ap.usuario.username,
            'animal_elegido': ap.animal_elegido,
            'codigo_animal': ap.animal_elegido,
            'nombre_animal': nombre_renderizado,
            'monto': ap.monto,
            'estado': ap.estado
        })
    return jsonify({'status': 'success', 'apuestas': resultado})


@app.route('/add_mercado', methods=['POST'])
@login_required
def add_mercado():
    if current_user.username != 'omarbri': return "No autorizado", 403
    fecha_dt = datetime.strptime(request.form.get('fecha_limite'), '%Y-%m-%dT%H:%M') if request.form.get('fecha_limite') else None
    db.session.add(Mercado(pregunta=request.form.get('pregunta'), fecha_cierre=fecha_dt, estado='Abierto'))
    db.session.commit()
    return redirect(url_for('admin'))

# --- INICIALIZACIÓN ---

with app.app_context():
    db.create_all()
    actualizar_tasa_dolar()
    
    # Buscamos si ya existe tu usuario administrador
    if not Usuario.query.filter_by(username='omarbri').first():
        # Obtenemos la contraseña de forma segura desde el archivo .env
        # Si no existe en el .env, usamos un fallback extremadamente seguro temporal
        admin_password = os.environ.get('ADMIN_PASSWORD', 'CambiarEstaClaveSuperSegura2026!')
        
        admin_user = Usuario(
            nombre_completo="Admin Omar", 
            cedula="00000000", 
            username='omarbri', 
            email='admin@teapuestovip.com', 
            telefono='000000000', 
            saldo=0.0
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        print("ℹ️ [Seguridad] Usuario administrador 'omarbri' creado con éxito desde variables de entorno.")

    config = Configuracion.query.first()
    if config and config.piloto_automatico:
        print("🤖 [Sistema] Verificando parrilla de sorteos para HOY tras reinicio del servidor...")
        hoy = get_hora_ve().date()
        ejecutar_programacion_parrilla(hoy)
@app.route('/actualizar_limites', methods=['POST'])
@login_required
def actualizar_limites():
    if current_user.username != 'omarbri':
        return "Acceso denegado", 403

    config = Configuracion.query.first()
    if config:
        config.animalitos_min = float(request.form.get('a_min', 1.0))
        config.animalitos_max = float(request.form.get('a_max', 500.0))
        config.mercados_min = float(request.form.get('m_min', 5.0))
        config.mercados_max = float(request.form.get('m_max', 1000.0))

        db.session.commit()
        return redirect(url_for('admin'))

    return "Error al cargar configuración", 500

@app.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
def gestionar_configuracion():
    if current_user.username != 'omarbri':
        return "No autorizado", 403

    config = db.session.get(Configuracion, 1)
    if not config:
        config = Configuracion(id=1, piloto_automatico=False)
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        datos = request.get_json()
        nuevo_estado = datos.get('activo', False)

        config.piloto_automatico = nuevo_estado
        db.session.commit()

        if nuevo_estado == True:
            print("[Piloto] Botón encendido manualmente. Verificando parrilla de HOY...")
            ejecutar_programacion_parrilla(get_hora_ve().date())

        estado_txt = "ACTIVADO" if nuevo_estado else "DESACTIVADO"
        return jsonify({
            "status": "success",
            "mensaje": f"Piloto automático {estado_txt} con éxito y verificado."
        })

    return render_template('admin.html', config=config)

@app.route('/detalle_mercado_apuestas/<int:mercado_id>')
@login_required
def detalle_mercado_apuestas(mercado_id):
    if current_user.username != 'omarbri': 
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 403
        
    apuestas = ApuestaMercado.query.filter_by(mercado_id=mercado_id).all()
    resultado = [{
        'username': ap.usuario.username,
        'opcion_elegida': ap.opcion_elegida,
        'monto': ap.monto,
        'estado': ap.estado
    } for ap in apuestas]

    return jsonify({
        'status': 'success',
        'apuestas': resultado
    })

# ==========================================
# 🔑 RECUPERACIÓN DE CONTRASEÑA
# ==========================================

@app.route('/olvide_password', methods=['GET', 'POST'])
def olvide_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = Usuario.query.filter_by(email=email).first()

        if user:
            token = serializer.dumps(email, salt='recuperar-password-salt')
            link = url_for('restablecer_password', token=token, _external=True)

            msg = Message('Recuperación de Contraseña - TEAPUESTOVIP', recipients=[email])
            msg.body = f"""Hola {user.nombre_completo},

Has solicitado restablecer tu contraseña en TEAPUESTOVIP. Haz clic en el siguiente enlace para crear una nueva contraseña:

{link}

Este enlace es válido por 30 minutos. Si no realizaste esta solicitud, puedes ignorar este correo.

Atentamente,
El equipo de TEAPUESTOVIP.
"""
            try:
                mail.send(msg)
                flash("Hemos enviado un enlace de recuperación a tu correo electrónico.")
            except Exception as e:
                print(f"❌ Error al enviar correo: {e}")
                flash("Hubo un error al enviar el correo. Revisa la configuración del servidor.")
        else:
            flash("Si el correo está registrado en el sistema, recibirás un enlace de recuperación.")

        return redirect(url_for('login'))

    return render_template('olvide_password.html')


@app.route('/restablecer_password/<token>', methods=['GET', 'POST'])
def restablecer_password(token):
    try:
        email = serializer.loads(token, salt='recuperar-password-salt', max_age=1800)
    except (SignatureExpired, BadTimeSignature):
        flash("El enlace de recuperación ha expirado o es inválido. Solicita uno nuevo.")
        return redirect(url_for('olvide_password'))

    user = Usuario.query.filter_by(email=email).first_or_404()

    if request.method == 'POST':
        nueva_clave = request.form.get('password')
        confirmar_clave = request.form.get('confirm_password')

        if not nueva_clave or nueva_clave != confirmar_clave:
            flash("Las contraseñas no coinciden o están vacías.")
            return render_template('restablecer_password.html', token=token)

        user.set_password(nueva_clave)
        db.session.commit()

        flash("¡Tu contraseña ha sido actualizada con éxito! Ya puedes iniciar sesión.")
        return redirect(url_for('login'))

    return render_template('restablecer_password.html', token=token)
if __name__ == '__main__':
    app.run(threaded=True, debug=False)

