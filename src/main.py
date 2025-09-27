from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def redirect_to_main():
    return jsonify({
        'message': 'This is a placeholder. The main app is at main_dynamic_pricing.py',
        'redirect': 'Use main_dynamic_pricing:app for the actual application'
    })

if __name__ == '__main__':
    app.run()
