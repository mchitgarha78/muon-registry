
from pyfrost.network.dkg import Dkg
from pyfrost.network.sa import SA
from node_evaluator import NodeEvaluator
from config import REGISTRY_INFO, PRIVATE
from common.node_info import NodeInfo
from common.data_manager import DataManager
from typing import List, Dict
import uuid
import random
import json
import requests
import time
import trio
import logging


class Registry:
    def __init__(self, total_node_number: int, registry_url: str) -> None:
        self.node_info = NodeInfo()
        self.dkg = Dkg(REGISTRY_INFO, PRIVATE, self.node_info,
                       max_workers=0, default_timeout=50)

        self.sa = SA(REGISTRY_INFO, PRIVATE, self.node_info, max_workers=0, default_timeout=50,
                     host=self.dkg.host)
        self.data_manager = DataManager()

        self.total_node_number = total_node_number
        self.registry_url = registry_url
        self.__nonces: Dict[str, list[Dict]] = {}
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def maintain_nonces(self, min_number_of_nonces: int = 10):
        all_nodes = self.node_info.get_all_nodes(self.total_node_number)
        selected_nodes = {}
        for node_id, peer_ids in all_nodes.items():
            selected_nodes[node_id] = peer_ids[0]
        nonces = await self.sa.request_nonces(selected_nodes, min_number_of_nonces)
        #self.node_evaluator.evaluate_responses(nonces)
        self.__nonces = nonces

    async def update_dkg_list(self) -> None:
        try:
            new_data: Dict = requests.get(self.registry_url).json()
            for id, data in new_data.items():
                self.dkg_list[id] = data
        except Exception as e:
            logging.error(
                f'Registry => Exception occurred: {type(e).__name__}: {e}')

    async def get_nonces(self, party: List[str], timeout: int = 5) -> Dict:
        commitments_dict = {}
        peer_ids_with_timeout = {}
        for peer_id in party:
            with trio.move_on_after(timeout) as cancel_scope:
                while not self.__nonces.get(peer_id):
                    await trio.sleep(0.1)

                commitment = self.__nonces[peer_id].pop()
                commitments_dict[peer_id] = commitment

            if cancel_scope.cancelled_caught:
                timeout_response = {
                    'status': 'TIMEOUT',
                    'error': 'Communication timed out',
                }
                peer_ids_with_timeout[peer_id] = timeout_response
        if len(peer_ids_with_timeout) > 0:
            self.node_evaluator.evaluate_responses(peer_ids_with_timeout)
            logging.warning(
                f'get_commitments => Timeout error occurred. peer ids with timeout: {peer_ids_with_timeout}')
        return commitments_dict

    async def run(self, args) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.dkg.run)
            await self.maintain_nonces()
            await self.update_dkg_list()
            if args.operation == 'predefined-party':
                await self.predefined_party_dkg(args.app_name, args.threshold, json.loads(args.party))
            elif args.operation == 'random-party':
                await self.random_party_dkg(args.app_name, args.threshold, args.party_number)
            self.dkg.stop()
            nursery.cancel_scope.cancel()

    @staticmethod
    def get_new_random_subset(dictionary: Dict, seed: int, subset_size: int) -> Dict:
        random.seed(seed)
        items = list(dictionary.items())
        if subset_size > len(items):
            raise ValueError(
                "Subset size cannot be greater than the length of the dictionary.")
        random_subset = random.sample(items, subset_size)
        random_subset_dict = dict(random_subset)
        return random_subset_dict

    async def random_party_dkg(self, app_name: str, threshold: int,  n: int):
        deployment_dkg_id = [key for key, value in self.dkg_list.items(
        ) if value['app_name'] == 'deployment'][0]
        timestamp = int(time.time())
        data = {
            'app': 'deployment',
            'method': 'get_random_seed',
            'reqId': str(uuid.uuid4()),
            'data': {
                'params': {
                    'app_name': app_name,
                    'timestamp': timestamp
                },
            }
        }

        deployment_dkg_key = self.dkg_list[deployment_dkg_id].copy()
        deployment_dkg_key['dkg_id'] = deployment_dkg_id
        commitments_dict = await self.get_nonces(deployment_dkg_key['party'])

        result = await self.sa.request_signature(deployment_dkg_key, commitments_dict, data, deployment_dkg_key['party'])
        if result['result'] == 'FAILED':
            self.node_evaluator.evaluate_responses(result['signatures'])
            return {
                'status': 'FAILED',
                'sign': result,
                'dkg_response': None
            }
        all_nodes = self.node_info.get_all_nodes(self.total_node_number)
        new_party = Registry.get_new_random_subset(
            all_nodes, int(result['message']['signature'], 16), n)
        new_party = self.node_evaluator.get_new_party(new_party, n)
        is_completed = False
        dkg_response = None
        while not is_completed:
            # TODO: remove app_name from request_dkg
            dkg_response = await self.dkg.request_dkg(threshold, new_party, None)
            if dkg_response['dkg_id'] == None:
                return {
                    'status': 'FAILED',
                    'sign': None,
                    'dkg_response': dkg_response
                }
            result = dkg_response['result']
            if result == 'SUCCESSFUL':
                is_completed = True
                break
            else:
                self.node_evaluator.evaluate_dkg_response(dkg_response)
        data = {
            'app': 'deployment',
            'method': 'verify_dkg_key',
            'reqId': str(uuid.uuid4()),
            'data': {
                'params': {
                    'app_name': app_name,
                    'timestamp': timestamp,
                    'seed': int(result['message']['signature'], 16),
                    'n': n,
                    'dkg_data': dkg_response,
                    'party': new_party,
                    'threshold': threshold,
                },

            }
        }

        commitments_dict = await self.get_nonces(deployment_dkg_key['party'])
        result = await self.sa.request_signature(deployment_dkg_key, commitments_dict, data, deployment_dkg_key['party'])
        if result['result'] == 'FAILED':
            self.node_evaluator.evaluate_responses(result['signatures'])
            print(json.dumps(result, indent=4))
            return {
                'status': 'FAILED',
                'sign': result,
                'dkg_response': None
            }

        res = {
            'status': 'SUCCESSFUL',
            dkg_response['dkg_id']: {
                'app_name': app_name,
                'threshold': threshold,
                'party': dkg_response['party'],
                'n': n,
                'public_key': dkg_response['public_key'],
                'public_shares': dkg_response['public_shares'],
                'is_predefined': False,
                'deployment_signature': result['signatures'],
                'timestamp': int(time.time())
            }
        }
        print(json.dumps(res, indent=4))
        return res

    async def predefined_party_dkg(self, app_name: str, threshold: int, party: List):
        is_completed = False
        dkg_response = None
        all_nodes = self.node_info.get_all_nodes(self.total_node_number)

        # TODO: Selected nodes should be random.
        selected_nodes = {}
        for node_id, peer_ids in all_nodes.items():
            selected_nodes[node_id] = peer_ids[0]
        dict_party = {}
        for node_id in party:
            dict_party[str(node_id)] = selected_nodes[str(node_id)]
        while not is_completed:
            dkg_response = await self.dkg.request_dkg(threshold, dict_party, None)
            if dkg_response['dkg_id'] == None:
                return {
                    'status': 'FAILED',
                    'sign': result,
                    'dkg_response': None
                }
            result = dkg_response['result']
            if result == 'SUCCESSFUL':
                is_completed = True
                res = {
                    dkg_response['dkg_id']: {
                        'app_name': app_name,
                        'threshold': threshold,
                        'party': dkg_response['party'],
                        'public_key': dkg_response['public_key'],
                        'public_shares': dkg_response['public_shares'],
                        'is_predefined': True,
                        'timestamp': int(time.time())
                    }
                }
                print(json.dumps(res, indent=4))
                return res
            else:
                self.node_evaluator.evaluate_dkg_response(dkg_response)
