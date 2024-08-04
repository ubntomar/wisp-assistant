from flask import Blueprint, render_template, current_app

router_bp = Blueprint('router', __name__, url_prefix='/router')

@router_bp.route('/<brand>')
def router_page(brand):
    network_connected = current_app.config['NETWORK_CONNECTED']
    return render_template('router.html', brand=brand, network_connected=network_connected)
