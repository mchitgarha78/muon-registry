from typing import Dict

import subprocess
import time
from datetime import datetime
import json


while True:
    with open('apps_list.json') as reader:
        apps_list = reader.read()
    
    apps_list: Dict = json.loads(apps_list)
    updated_list = {}
    for dkg_id, data in apps_list.items():
        if data['is_predifined'] is True:
            updated_list[dkg_id] = data
            continue
        date = datetime.fromtimestamp(data['timestamp'])
        delta = datetime.now() - date
        if delta.days >= 1:
            # TODO : Run dkg commandline for random party.
            output = subprocess.run(f'python command_line.py python command_line.py dkg -m random -t 1 -a simple_oracle -n 1 -p ["16Uiu2HAkv3kvbv1LjsxQ62kXE8mmY16R97svaMFhZkrkXaXSBSTq"]')
            updated_list[dkg_id] = json.loads(output)
    time.sleep(5 * 60)