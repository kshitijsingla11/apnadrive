import os
from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config['DOMAIN_NAME'] = "http:/princemehta04.pythonanywhere.com/"
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, "uploads")
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    try:
        os.makedirs(app.instance_path)
        os.makedirs(os.path.join(app.instance_path, "uploads"))
    except OSError:
        print("some error")
    from . import db
    db.init_app(app)
    from . import auth
    app.register_blueprint(auth.bp)
    from . import myfiles
    app.register_blueprint(myfiles.bp)
    app.add_url_rule('/', endpoint='index')
    return app
