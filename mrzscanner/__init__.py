from .mrzscanner import * 
import os
import json
__version__ = version
    
def get_model_path():
    config_file = os.path.join(os.path.dirname(__file__), 'MRZ.json')
    try:
        # open json file
        with open(config_file, 'r+') as f:
            data = json.load(f)
            if data['CharacterModelArray'][0]['DirectoryPath'] == 'model':
                data['CharacterModelArray'][0]['DirectoryPath'] = os.path.join(os.path.dirname(__file__), 'model')
                # print(data['CharacterModelArray'][0]['DirectoryPath'])
                
                # write json file
                f.seek(0) # rewind
                f.write(json.dumps(data))
    except Exception as e:
        print(e)
        pass
    
    return config_file
    