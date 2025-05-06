from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
import requests
import json
import os
from dotenv import load_dotenv
# -------------------- API TOKENS --------------------

SUREPASS_CAR_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTczNDE3MTI4OCwianRpIjoiNDI0ZmM1ZmYtYzBmOC00YmYxLWE1MWQtMmVkYmMyN2Q4YjZhIiwidHlwZSI6ImFjY2VzcyIsImlkZW50aXR5IjoiZGV2LmJhZGFmaW5hbmNlX2NvbnNvbGVAc3VyZXBhc3MuaW8iLCJuYmYiOjE3MzQxNzEyODgsImV4cCI6MjM2NDg5MTI4OCwiZW1haWwiOiJiYWRhZmluYW5jZV9jb25zb2xlQHN1cmVwYXNzLmlvIiwidGVuYW50X2lkIjoibWFpbiIsInVzZXJfY2xhaW1zIjp7InNjb3BlcyI6WyJ1c2VyIl19fQ.md1Oaj19QbxeXmjyfdRMJMF50j9c9i_oPtX2UreFKKM"
SUREPASS_CIBIL_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTczNDE3MTI4OCwianRpIjoiNDI0ZmM1ZmYtYzBmOC00YmYxLWE1MWQtMmVkYmMyN2Q4YjZhIiwidHlwZSI6ImFjY2VzcyIsImlkZW50aXR5IjoiZGV2LmJhZGFmaW5hbmNlX2NvbnNvbGVAc3VyZXBhc3MuaW8iLCJuYmYiOjE3MzQxNzEyODgsImV4cCI6MjM2NDg5MTI4OCwiZW1haWwiOiJiYWRhZmluYW5jZV9jb25zb2xlQHN1cmVwYXNzLmlvIiwidGVuYW50X2lkIjoibWFpbiIsInVzZXJfY2xhaW1zIjp7InNjb3BlcyI6WyJ1c2VyIl19fQ.md1Oaj19QbxeXmjyfdRMJMF50j9c9i_oPtX2UreFKKM"

# -------------------- Firebase Setup --------------------

load_dotenv()

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})

# -------------------- Flask App --------------------

app = Flask(__name__)

# -------------------- Car Report Logic --------------------

def fetch_car_data(id_number):
    url = "https://kyc-api.surepass.io/api/v1/rc/rc-full"
    payload = {"id_number": id_number}
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SUREPASS_CAR_TOKEN}'
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def check_existing_car_data(id_number):
    return db.reference(f'car_reports/{id_number}').get()

def save_car_data(id_number, data):
    db.reference(f'car_reports/{id_number}').set(data)

@app.route('/fetch_car', methods=['POST'])
def fetch_and_store_car():
    content = request.get_json()
    id_number = content.get('id_number')
    if not id_number:
        return jsonify({"error": "Missing id_number"}), 400

    existing = check_existing_car_data(id_number)
    if existing:
        return jsonify({
            "message": f"Car data for {id_number} already exists.",
            "data": existing,
            "overwrite_url": f"/overwrite_car"
        }), 200

    data = fetch_car_data(id_number)
    if 'error' in data:
        return jsonify({"error": data['error']}), 500

    save_car_data(id_number, data)
    return jsonify({"message": f"Car data saved for {id_number}", "data": data}), 200

@app.route('/overwrite_car', methods=['POST'])
def overwrite_car():
    content = request.get_json()
    id_number = content.get('id_number')
    if not id_number:
        return jsonify({"error": "Missing id_number"}), 400

    data = fetch_car_data(id_number)
    if 'error' in data:
        return jsonify({"error": data['error']}), 500

    save_car_data(id_number, data)
    return jsonify({"message": f"Overwritten car data for {id_number}", "data": data}), 200

@app.route('/get_car', methods=['GET'])
def get_car():
    id_number = request.args.get('id_number')
    if not id_number:
        return jsonify({"error": "Missing id_number"}), 400

    data = check_existing_car_data(id_number)
    if not data:
        return jsonify({"message": "No car data found"}), 404

    return jsonify({"data": data}), 200

# -------------------- CIBIL Report Logic --------------------

def fetch_cibil_data(mobile, pan, name, gender, consent):
    url = "https://kyc-api.surepass.io/api/v1/credit-report-cibil/fetch-report"
    payload = {
        "mobile": mobile,
        "pan": pan,
        "name": name,
        "gender": gender.lower(),
        "consent": consent
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SUREPASS_CIBIL_TOKEN}'
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def check_existing_cibil_data(pan):
    return db.reference(f'cibil_reports/{pan}').get()

def save_cibil_data(pan, data):
    db.reference(f'cibil_reports/{pan}').set(data)

@app.route('/fetch_cibil', methods=['POST'])
def fetch_and_store_cibil():
    content = request.get_json()
    required = ['mobile', 'pan', 'name', 'gender', 'consent']
    if not all(field in content for field in required):
        return jsonify({"error": "Missing one or more required fields"}), 400

    pan = content['pan']
    existing = check_existing_cibil_data(pan)
    if existing:
        return jsonify({
            "message": f"CIBIL data for {pan} already exists.",
            "data": existing,
            "overwrite_url": f"/overwrite_cibil"
        }), 200

    data = fetch_cibil_data(content['mobile'], pan, content['name'], content['gender'], content['consent'])
    if 'error' in data:
        return jsonify({"error": data['error']}), 500

    save_cibil_data(pan, data)
    return jsonify({"message": f"CIBIL data saved for {pan}", "data": data}), 200

@app.route('/overwrite_cibil', methods=['POST'])
def overwrite_cibil():
    content = request.get_json()
    required = ['mobile', 'pan', 'name', 'gender', 'consent']
    if not all(field in content for field in required):
        return jsonify({"error": "Missing one or more required fields"}), 400

    data = fetch_cibil_data(content['mobile'], content['pan'], content['name'], content['gender'], content['consent'])
    if 'error' in data:
        return jsonify({"error": data['error']}), 500

    save_cibil_data(content['pan'], data)
    return jsonify({"message": f"CIBIL data overwritten for {content['pan']}", "data": data}), 200

@app.route('/get_cibil', methods=['GET'])
def get_cibil():
    pan = request.args.get('pan')
    if not pan:
        return jsonify({"error": "Missing pan"}), 400

    data = check_existing_cibil_data(pan)
    if not data:
        return jsonify({"message": "No CIBIL data found"}), 404

    return jsonify({"data": data}), 200


@app.route('/fetch_cibil_by_pan', methods=['POST'])
def fetch_cibil_by_pan():
    content = request.get_json()
    pan = content.get('pan')
    
    if not pan:
        return jsonify({"error": "Missing PAN"}), 400

    data = check_existing_cibil_data(pan)
    if not data:
        return jsonify({"error": f"No CIBIL data found for PAN: {pan}"}), 404

    return jsonify({"status": "success", "data": data}), 200


# -------------------- Home --------------------

@app.route('/')
def home():
    return "✅ Flask API for Car & CIBIL data with Firebase is running!"

# -------------------- Run App --------------------

if __name__ == '__main__':
    app.run(debug=True)
