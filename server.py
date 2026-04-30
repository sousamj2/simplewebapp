from waitress import serve
from explicolivais import app
import sys
import os
sys.path.insert(0,os.getcwd()+"/DBhelpers")

import DBbaseline
import DBloadQuiz

import os
import logging

# Configurar logging
logging.getLogger('waitress.queue').setLevel(logging.ERROR)


if __name__ == '__main__':
    DBbaseline.setup_mysql_database();
    DBloadQuiz.loadQanswers();
    DBloadQuiz.loadQlinks();
    DBloadQuiz.loadQtemas();
    DBloadQuiz.loadQaulas();
    
    # For production use waitress to serve the app

    # Localhost access only
    # serve(app, host="localhost", port=8080, threads=8, channel_timeout=120,connection_limit=100,backlog=2048 )
    serve(app, host='0.0.0.0', port=8080, threads=8, channel_timeout=120,connection_limit=100,backlog=2048 )
