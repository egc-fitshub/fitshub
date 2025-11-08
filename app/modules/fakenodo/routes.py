from flask import render_template
from app.modules.fakenodo import fakenodo_bp
from app.modules.fakenodo.services import FakenodoService


@fakenodo_bp.route('/fakenodo', methods=['GET'])
def index():
    return render_template('fakenodo/index.html')

@fakenodo_bp.route('/fakenodo/test', methods=['GET'])
def fakenodo_test():
    service = FakenodoService()
    return service.test_full_connection()
