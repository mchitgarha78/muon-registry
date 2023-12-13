from flask import Flask, request, jsonify
import json
import logging
app = Flask(__name__)

@app.route('/v1/', methods=['GET'])
def get_app_list():
    try:
        with open('apps_list.json', 'r') as apps_list_reader:
            response_data = json.loads(apps_list_reader.read())
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(f'Flask get_app_list => Exception occurred: {type(e).__name__}: {e}')
        return jsonify({'error': 'Internal server error.'}), 500


if __name__ == '__main__':
    app.run(port = 8050, debug = True, use_reloader = False)