from flask import Flask, render_template, send_file, request
from werkzeug.serving import make_server
import webbrowser as wb
from threading import Thread
from time import sleep
import logging
import requests
import sys
from functools import reduce 


logger = logging.getLogger()
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))
log = logger


def put_tree_value(tree, keys, value):
    if len(keys) == 0:
        return value
    key = keys[0]
    new_keys = keys[1:]
    tree[key] = put_tree_value(tree.get(key, {}), new_keys, value)
    return tree

def make_one_setting_tree(tree, key_value):
    key, value = key_value
    keys = key.split('.')
    return put_tree_value(tree, keys, value)

def make_settings_tree(settings):
    return reduce(make_one_setting_tree, settings.items(), {})


class ServerThread(Thread):

    def __init__(self, app):
        Thread.__init__(self)
        self.srv = make_server('127.0.0.1', 6008, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        log.info('starting server')
        self.srv.serve_forever()

    def shutdown(self):
        log.info('stopping server')
        self.srv.shutdown()


def create_server():
    app = Flask(__name__, root_path="web/build", 
                          static_folder="static",
                          template_folder="")
    server = ServerThread(app)

    @app.route("/")
    def index():
        return send_file("index.html")
        
    @app.route("/<filename>")
    def static_root(filename):
        return send_file(filename)

    @app.route('/static/<path>')
    def static_normal(path):
        return send_file('static/' + path)
        
    @app.route('/static/js/<path>')
    def static_js(path):
        return send_file('static/js/'+ path)
        
    @app.route("/api/v1.0/alive")
    def alive():
        return "ok"
        
    @app.route("/api/v1.0/set-settings", methods = ['POST'])
    def set_settings():
        settings = request.json
        log.info(str(make_settings_tree(settings)))
        return "ok"
        
    @app.route("/api/v1.0/clear-gdrive-creds", methods = ['POST'])
    def clear_gdrive_credentials():
        return "ok"
        
    @app.route("/api/v1.0/start-gdrive-auth", methods = ['POST'])
    def authenticate_gdrive():
        return "ok"
        
    @app.route("/api/v1.0/quit")
    def quit():
        stop_thread = Thread(target=lambda: server.shutdown())
        stop_thread.start()
        return "ok"
        
    return server

    
if __name__ == "__main__":
    
    def open_tab():
        started = False
        while not started:
            try:
                r = requests.get(url='http://127.0.0.1:6008/api/v1.0/alive', 
                                 timeout=0.5) 
                code = r.status_code
                if code >= 200 and code < 300:
                    started = True
            except Exception:
                continue
        wb.open_new_tab('http://127.0.0.1:6008')
    
    server = create_server()
    server.start()
    open_tab()
