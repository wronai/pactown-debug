"""Pactfix API Server - Flask-based REST API for code analysis."""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from .analyzer import analyze_code, detect_language, SUPPORTED_LANGUAGES

app = Flask(__name__)
CORS(app)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'pactfix',
        'version': '1.0.0',
        'supported_languages': SUPPORTED_LANGUAGES
    })


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze code endpoint."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        code = data.get('code', '')
        filename = data.get('filename')
        language = data.get('language')
        
        if not code:
            return jsonify({
                'language': 'unknown',
                'originalCode': '',
                'fixedCode': '',
                'errors': [],
                'warnings': [],
                'fixes': [],
                'context': {}
            })
        
        result = analyze_code(code, filename, language)
        return jsonify(result.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect', methods=['POST'])
def detect():
    """Detect language endpoint."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        code = data.get('code', '')
        filename = data.get('filename')
        
        language = detect_language(code, filename)
        return jsonify({'language': language})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/languages', methods=['GET'])
def languages():
    """List supported languages."""
    return jsonify({
        'languages': SUPPORTED_LANGUAGES,
        'categories': {
            'code': ['bash', 'python', 'php', 'javascript', 'nodejs'],
            'config': ['dockerfile', 'docker-compose', 'nginx', 'github-actions', 'ansible'],
            'data': ['sql', 'terraform', 'kubernetes']
        }
    })


def create_app():
    """Application factory."""
    return app


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the Flask server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    run_server(port=port, debug=debug)
