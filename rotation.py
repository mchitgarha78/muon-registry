from registy import Registry
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
import json
import sys
import trio
import os


PERIOD_IN_SECONDS = 24 * 60 * 60
NUMBER_OF_RETRY = 10

if __name__ == '__main__':
    load_dotenv()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    total_node_number = sys.argv[1]
    registry = Registry(os.getenv('APPS_LIST_URL'), os.getenv('PRIVATE_KEY'), os.getenv('HOST'), os.getenv('PORT'))
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
