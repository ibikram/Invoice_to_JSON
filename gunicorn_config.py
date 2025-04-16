import os

# Create logs folder if it doesn't exist
logs_folder = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(logs_folder):
    os.makedirs(logs_folder)

# Gunicorn configuration
bind = "0.0.0.0:8000"
workers = 2
timeout = 600
accesslog = os.path.join(logs_folder, 'access.log')
errorlog = os.path.join(logs_folder, 'error.log')
loglevel = 'info'