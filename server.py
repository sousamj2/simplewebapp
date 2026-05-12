import os
import sys
import logging
from waitress import serve
from werkzeug.middleware.proxy_fix import ProxyFix

# Add parent directory and mysql directory to path to allow importing our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../mysql')))

from app import create_app
from DBhelpers import DBbaseline

# Configure logging for Waitress
logging.getLogger('waitress.queue').setLevel(logging.ERROR)

if __name__ == '__main__':
    print("🚀 Initializing Minecraft Portal Server...")
    
    # 1. Setup the database tables if they don't exist (matching runFlask.sh logic)
    print("   📦 Checking database tables...")
    DBbaseline.setup_mysql_database()
    print("   ✅ Database is ready.")

    # 2. Create the application instance using the factory pattern
    # Determine config from environment, defaulting to 'production' for server.py
    env = os.getenv('FLASK_ENV', 'production')
    app = create_app(env)
    
    # 3. Apply ProxyFix (matching app.py for robust IP/protocol detection)
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1
    )
    
    @app.before_request
    def log_request_info():
        from flask import request
        # Only log for authentication/registration routes to keep logs clean
        if any(x in request.path for x in ['signin', 'oauth2', 'signup', 'updateDB']):
            print(f"\n[DEBUG] --- Incoming Request: {request.path} ---", flush=True)
            print(f"[DEBUG] Host Header: {request.headers.get('Host')}", flush=True)
            print(f"[DEBUG] X-Forwarded-Proto: {request.headers.get('X-Forwarded-Proto')}", flush=True)
            print(f"[DEBUG] X-Forwarded-Host: {request.headers.get('X-Forwarded-Host')}", flush=True)
            print(f"[DEBUG] Flask thinks URL is: {request.url}", flush=True)
    
    # 4. Start the Production Server
    port = 8081
    print(f"🚀 Starting Waitress Production Server on port {port}...")
    print(f"📍 Access URL: https://mc.mjcrafts.pt")
    print(f"📍 Access URL: http://localhost:{port}")
    
    serve(
        app, 
        host='*', 
        port=port, 
        threads=8, 
        channel_timeout=120, 
        connection_limit=100, 
        backlog=2048,
        trusted_proxy='*', # Trust headers from all proxies (since we handle it via ProxyFix)
        trusted_proxy_headers=['x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host', 'x-forwarded-port']
    )
