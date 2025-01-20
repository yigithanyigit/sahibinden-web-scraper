import os

# Get the base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define all file paths relative to base directory
PATHS = {
    'STATE_FILE': os.path.join(BASE_DIR, 'data', 'state', 'current_state.json'),
    'CONTINUOUS_DATA': os.path.join(BASE_DIR, 'data', 'listings', 'continuous_data.json'),
    'DEFAULT_EXPORT': os.path.join(BASE_DIR, 'data', 'exports'),
}

# Create necessary directories
for path in PATHS.values():
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
