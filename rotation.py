from registy import Registry
from config import APPS_LIST_URL
from datetime import datetime
from typing import Dict
import json
import sys
import trio
import os


PERIOD_IN_SECONDS = 24 * 60 * 60
NUMBER_OF_RETRY = 10

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    total_node_number = sys.argv[1]
    registry = Registry(total_node_number, APPS_LIST_URL)
    with open('apps.json') as reader:
        apps_list = reader.read()
    apps_list: Dict = json.loads(apps_list)
    updated_list = {}
    for dkg_id, data in apps_list.items():
        if data['is_predefined']:
            updated_list[dkg_id] = data
            continue
        time_delta = datetime.now() - datetime.fromtimestamp(data['timestamp'])
        if time_delta.total_seconds() > PERIOD_IN_SECONDS:
            for _ in range(NUMBER_OF_RETRY):
                result = trio.run(lambda: registry.random_party_dkg(
                    data['app_name'], data['threshold'], data['n']))
                if result['status'] != 'SUCCESSFUL':
                    continue
                updated_list[dkg_id] = json.loads(result)
                break
    with open('apps.json', 'w') as writer:
        apps_list = writer.write(json.dumps(updated_list, indent=4))
