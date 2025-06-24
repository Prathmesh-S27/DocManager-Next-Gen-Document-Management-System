from flask import Flask, Blueprint
from flask import request, jsonify
from flask_cors import CORS, cross_origin

testing_bp = Blueprint('testing', __name__ ,url_prefix='/test') 

@testing_bp.route('/testing', methods=['GET'])
def testing():
    return 'Testing Serve in running! for testign 1'