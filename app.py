import os
import sys
# Add parent directory to path to allow importing our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../mysql')))

from flask import Flask, redirect, render_template
from pprint import pprint
from werkzeug.middleware.proxy_fix import ProxyFix

from dotenv import load_dotenv
load_dotenv()

from mailinteraction import mail
from authenticate import (
    bp_check_user, bp_logout, bp_oauth2callback, bp_signin, 
    bp_signup, bp_signin_redirect, bp_updateDB
)
from mailinteraction import bp_register, bp_request_new_user
from blueprints import (
    bp_home, bp_profile, 
    bp_calendar, bp_adminDB
)



def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__,
                static_folder='static',
                static_url_path='/static'
                )

    # Determine which config to use
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize Flask-Mail via the extension pattern to avoid assigning new attributes on Flask
    mail.init_app(app)
    # print("Mail state after init_app:", mail.state)
    
    # Favicon route
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('images/favicon.png')
    
    app.register_blueprint(bp_check_user)
    app.register_blueprint(bp_logout)
    app.register_blueprint(bp_oauth2callback)
    app.register_blueprint(bp_home)
    app.register_blueprint(bp_profile)
    app.register_blueprint(bp_signin_redirect)
    app.register_blueprint(bp_signin)
    app.register_blueprint(bp_signup)
    app.register_blueprint(bp_register)
    app.register_blueprint(bp_request_new_user)
    app.register_blueprint(bp_calendar)
    app.register_blueprint(bp_adminDB)
    app.register_blueprint(bp_updateDB)
    
    
    # Main route: redirect to /pages/ (home)
    @app.route('/')
    def index():
        return redirect('/')
    
    return app


# Create the app
app = create_app()
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Number of values to trust in X-Forwarded-For
    x_proto=1,
    x_host=1,
    x_port=1,
    x_prefix=1
)


if __name__ == '__main__':
    app.run()

# with app.app_context():
#     # from connectDB import check_and_create_users_table
#     # check_and_create_users_table()
#     pass