from flask import Blueprint, render_template, jsonify, session
deepdive_bp = Blueprint('deepdive', __name__)

@deepdive_bp.route('/deepdive')
def deepdive_page():
    streak = session.get('reading_streak', 12)
    return render_template('deepdive.html', streak=streak)
