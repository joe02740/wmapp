from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Flask is working!'})

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'API test working!', 'user_id': request.args.get('user_id')})

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)