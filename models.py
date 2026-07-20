from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from constantes import ANIMALITOS, COMISION_CASA_PORCENTAJE

# Creamos el objeto db sin conectarlo a la app todavía
db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    saldo = db.Column(db.Float, default=0.0)

    # Restricción de seguridad para el saldo
    __table_args__ = (
        db.CheckConstraint('saldo >= 0', name='check_saldo_positivo'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Sorteo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_animal = db.Column(db.String(50), nullable=True) # Se llena al finalizar
    numero = db.Column(db.String(10), nullable=True)        # Se llena al finalizar
    horario = db.Column(db.DateTime, nullable=False)        # Fecha y hora programada
    estado = db.Column(db.String(20), default='PROGRAMADO') # PROGRAMADO, CERRADO, FINALIZADO
    fecha_registro = db.Column(db.DateTime, default=datetime.now)
    
    # Relación con las apuestas de este sorteo
    apuestas = db.relationship('ApuestaAnimalito', backref='sorteo', lazy=True)


class ApuestaAnimalito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    sorteo_id = db.Column(db.Integer, db.ForeignKey('sorteo.id'), nullable=False)
    animal_elegido = db.Column(db.String(10), nullable=False) # El número apostado (0-36)
    monto = db.Column(db.Float, nullable=False)
    monto_ganado = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(20), default='PENDIENTE') # PENDIENTE, GANADA, PERDIDA
    fecha = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='apuestas_animalitos')


class Mercado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pregunta = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(20), default='Abierto')
    fecha_cierre = db.Column(db.DateTime, nullable=True)
    resultado_final = db.Column(db.String(10), nullable=True)
    apuestas_vinculadas = db.relationship('ApuestaMercado', backref='mercado', lazy=True)

    @property
    def total_apostado(self):
        return sum(apuesta.monto for apuesta in self.apuestas_vinculadas)

    @property
    def comision_casa(self):
        return self.total_apostado * COMISION_CASA_PORCENTAJE

    @property
    def total_si(self):
        return sum(apuesta.monto for apuesta in self.apuestas_vinculadas if apuesta.opcion_elegida == 'SI')

    @property
    def total_no(self):
        return sum(apuesta.monto for apuesta in self.apuestas_vinculadas if apuesta.opcion_elegida == 'NO')

    @property
    def pozo_neto(self):
        return self.total_apostado - self.comision_casa

    @property
    def cuota_si(self):
        if self.total_si > 0:
            return round((self.total_apostado / self.total_si) * 0.95, 2)
        return 0.0
    
    @property
    def cuota_no(self):
        total_apuestas = self.total_si + self.total_no
        if self.total_no > 0:
            return round((total_apuestas / self.total_no) * 0.95, 2)
        return 0.0


class ApuestaMercado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mercado_id = db.Column(db.Integer, db.ForeignKey('mercado.id'), nullable=False)
    opcion_elegida = db.Column(db.String(10), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='PENDIENTE')
    fecha = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='apuestas_mercado')
    monto_ganado = db.Column(db.Float, default=0.0)


class Movimiento(db.Model):
    __tablename__ = 'movimientos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) 
    tipo = db.Column(db.String(30)) # Se expandió a 30 para tipos largos como 'APUESTA_ANIMALITO'
    monto = db.Column(db.Float)
    
    # Datos de transacciones bancarias tradicionales
    referencia = db.Column(db.String(20), nullable=True)
    banco_emisor = db.Column(db.String(100), nullable=True)
    estatus = db.Column(db.String(20))
    fecha_transaccion = db.Column(db.DateTime, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.now)
    
    # ◄ NUEVOS CAMPOS ADAPTADOS: Apuntan a 'sorteo.id' y 'mercado.id' (en singular tal como tus modelos)
    sorteo_id = db.Column(db.Integer, db.ForeignKey('sorteo.id'), nullable=True)
    mercado_id = db.Column(db.Integer, db.ForeignKey('mercado.id'), nullable=True)
    detalle = db.Column(db.String(255), nullable=True)

    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('movimientos', lazy=True))
    sorteo = db.relationship('Sorteo', backref=db.backref('movimientos_financieros', lazy=True))
    mercado = db.relationship('Mercado', backref=db.backref('movimientos_financieros', lazy=True))


class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    id = db.Column(db.Integer, primary_key=True)
    
    # Límites para Animalitos
    animalitos_min = db.Column(db.Float, default=1.0)
    animalitos_max = db.Column(db.Float, default=500.0)
    
    # Límites para Mercados de Predicción
    mercados_min = db.Column(db.Float, default=5.0)
    mercados_max = db.Column(db.Float, default=1000.0)

    piloto_automatico = db.Column(db.Boolean, default=False)
    tasa_dolar_dia = db.Column(db.Float, default=0.0)
    fondo_semilla_optimo = db.Column(db.Float, default=0.0)
    caja_real_disponible = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<Configuracion Animalitos: {self.animalitos_min}-{self.animalitos_max} | Piloto: {self.piloto_automatico}>'
    
class SesionCaja(db.Model):
    __tablename__ = 'sesiones_caja'
    id = db.Column(db.Integer, primary_key=True)
    
    fecha_apertura = db.Column(db.DateTime, default=datetime.now, nullable=False)
    fecha_cierre = db.Column(db.DateTime, nullable=True) # Registra el momento exacto del cierre híbrido
    
    monto_apertura_bs = db.Column(db.Float, default=0.0, nullable=False)
    monto_cierre_sistema = db.Column(db.Float, default=0.0, nullable=False)
    monto_cierre_real = db.Column(db.Float, default=0.0, nullable=True) # Nullable hasta que se ejecute la conciliación/declaración manual
    discrepancy = db.Column(db.Float, default=0.0, nullable=False)     # Diferencia: Real - Sistema
    
    # Estados de la sesión: 'Abierta', 'Cerrada', 'Cerrada con Déficit', 'Cerrada con Superávit'
    estado = db.Column(db.String(50), default='Abierta', nullable=False)

    def __repr__(self):
        return f'<SesionCaja {self.id} - Estado: {self.estado} - Apertura: {self.fecha_apertura.strftime("%Y-%m-%d %H:%M")}>'    