from .mrzscanner import * 
import os
__version__ = version

def get_model_path():
    config_path = os.path.join(os.path.dirname(__file__), 'MRZ.json')
    print("Model path: " + config_path)
    return config_path
    