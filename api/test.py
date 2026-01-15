from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'Test API is working'})

# Vercel expects the app to be exported
export = app
