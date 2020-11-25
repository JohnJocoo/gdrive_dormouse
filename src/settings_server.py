from typing import Callable, Any
from flask import Flask, render_template, send_file, request
from werkzeug.serving import make_server
import webbrowser as wb
from threading import Thread, Timer, Lock
from time import sleep, time
import logging
import requests
from functools import reduce 
import json


NewSettingsCallback = Callable[[dict], Any]


class AlreadyRunning(RuntimeError):
    """Settings server already running."""
    pass


log = logging.getLogger('SettingsServer')


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
    
def make_settings_flat_impl(tree, path_list, key_value):
    key, value = key_value
    path_list = path_list + '.' + key
    if isinstance(value, dict):
        merge_fun = lambda tree, kv: make_settings_flat_impl(tree, path_list, kv)
        return reduce(merge_fun, value.items(), tree)
    tree[path_list] = value
    return tree
    
def make_settings_flat(settings):
    merge_fun = lambda tree, kv: make_settings_flat_impl(tree, '', kv)
    flat_settings = reduce(merge_fun, settings.items(), {})
    return {k[1:]: v for k, v in flat_settings.items()}

class ServerThread(Thread):

    def __init__(self, app, host, port):
        Thread.__init__(self, name='SettingsServerThread')
        self._lock = Lock()
        self._last_alive = None
        self._shutdown_no_alive_sec = 3.0
        self._alive_timer_sec = 1
        self._alive_timer_sec_initial = 5
        self._srv = make_server(host, port, app)
        self._ctx = app.app_context()
        self._ctx.push()
        self._timer = Timer(self._alive_timer_sec_initial, self.test_alive)
        self._timer.start()

    def touch_alive(self):
        self._lock.acquire()
        try:
            self._last_alive = time()
        finally:
            self._lock.release()
        
    def test_alive(self):
        last_alive = None
        self._lock.acquire()
        try:
            last_alive = self._last_alive
            self._timer = Timer(self._alive_timer_sec, self.test_alive)
        finally:
            self._lock.release()
        if last_alive is None:
            self.shutdown()
            return
        if (time() - last_alive) > self._shutdown_no_alive_sec:
            self.shutdown()
            return
        self._timer.start()

    def run(self):
        log.info('starting server')
        self._srv.serve_forever()
        log.info('server stopped')

    def shutdown(self):
        log.info('stopping server')
        self._lock.acquire()
        try:
            self._last_alive = None
            self._timer.cancel()
        finally:
            self._lock.release()
        self._srv.shutdown()

def read_version():
    try:
        with open('version.txt') as v_file:
            return v_file.read()
    except Exception:
        return '-.-.-'
        
def to_bool(value):
    if isinstance(value, bool):
        return value
    if value == 'true':
        return True
    if value == 'false':
        return False
    raise ValueError()

def create_server(host, port, settings_tree, callback):
    type_convertion_map = {
        'settings.monitoring.wait_time': lambda val: int(val),
        'settings.file_handler.dirs_as_jobs': to_bool,
        'settings.file_handler.add_time_job_name': to_bool}
    settings_saved = make_settings_flat(settings_tree)
    
    def type_convert(key, value):
        if key in type_convertion_map:
            return type_convertion_map[key](value)
        return value
    
    app = Flask(__name__, root_path='web/build', 
                          static_folder='static',
                          template_folder='')
    server = ServerThread(app, host, port)

    @app.route('/')
    def index():
        context_dict = {
            'version': read_version(),
            'default_settings': json.dumps(settings_saved)
        }
        return render_template('index.html', context=context_dict)
        
    @app.route('/<filename>')
    def static_root(filename):
        return send_file(filename)

    @app.route('/static/<path>')
    def static_normal(path):
        return send_file('static/' + path)
        
    @app.route('/static/js/<path>')
    def static_js(path):
        return send_file('static/js/'+ path)
        
    @app.route('/api/v1.0/alive')
    def alive():
        server.touch_alive()
        return 'ok'
        
    @app.route('/api/v1.0/get-settings')
    def get_settings():
        return json.dumps(settings_saved)
        
    @app.route('/api/v1.0/set-settings', methods = ['POST'])
    def set_settings():
        settings = request.json
        settings = {k: type_convert(k, v) for k, v in settings.items()}
        settings_saved = settings
        callback(make_settings_tree(settings))
        return 'ok'
        
    @app.route('/api/v1.0/clear-gdrive-creds', methods = ['POST'])
    def clear_gdrive_credentials():
        return 'ok'
        
    @app.route('/api/v1.0/start-gdrive-auth', methods = ['POST'])
    def authenticate_gdrive():
        return "ok"
        
    @app.route('/api/v1.0/quit')
    def quit():
        stop_thread = Thread(name='SettingsServerShutdownThread',
                             target=lambda: server.shutdown())
        stop_thread.start()
        return 'ok'
        
    return server

def open_tab(host, port):
    started = False
    i = 0
    while not started and i < 10:
        i = i + 1
        try:
            r = requests.get(url='http://{}:{}/api/v1.0/alive'.format(host, port), 
                             timeout=0.5) 
            code = r.status_code
            if code >= 200 and code < 300:
                started = True
        except Exception:
            continue
    wb.open_new_tab('http://{}:{}'.format(host, port))

def start_impl(host: str, port: int, 
               settings: dict, callback: NewSettingsCallback):
    server = create_server(host, port, settings, callback)
    server.start()
    Thread(name='OpenBrowserTabThread',
           target=lambda: open_tab(host, port)).start()
    

def start(host: str, port: int, 
          settings: dict, callback: NewSettingsCallback):
    r = None
    try:
        r = requests.get(url='http://{}:{}/api/v1.0/alive'.format(host, port), 
                         timeout=3) 
    except Exception:
        start_impl(host, port, settings, callback)
        return
    code = r.status_code
    if code >= 200 and code < 300:
        raise AlreadyRunning('Response code {}'.format(code))
    start_impl(host, port, settings, callback)

def main():
    import sys
    
    log.level = logging.DEBUG
    log.addHandler(logging.StreamHandler(sys.stdout))
    
    def log_settings(settings):
        log.info('settings updated:')
        log.info(json.dumps(settings))

    settings = {}
    with open('config/default_settings.json') as json_file:
        settings = json.load(json_file)
    start('127.0.0.1', 6008, settings, log_settings)


if __name__== "__main__":
    main()
