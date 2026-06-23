from flask import Blueprint, jsonify
from models import Sorteo

consultas_bp = Blueprint('consultas', __name__)

@consultas_bp.route('/api/sorteos_disponibles', methods=['GET'])
def sorteos_disponibles():
    # Buscamos sorteos PENDIENTES o PROGRAMADOS
    activos = Sorteo.query.filter(Sorteo.estado.in_(['PENDIENTE', 'PROGRAMADO'])).all()
    lista = [{'id': s.id, 'horario': s.horario.strftime("%H:%M")} for s in activos]
    return jsonify({'status': 'success', 'data': lista})