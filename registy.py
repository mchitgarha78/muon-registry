
from pyfrost.network.dkg import Dkg
from pyfrost.network.sa import SA
from node_evaluator import NodeEvaluator
from abstract.node_info import NodeInfo
from typing import List, Dict
from libp2p.crypto.secp256k1 import create_new_key_pair
from libp2p.peer.id import ID as PeerID
import uuid
import random
import json
import requests
import time
import trio
import logging


class Registry:
    def __init__(self, registry_url: str, private_key: str, host: str, port: str) -> None:
        self.node_info = NodeInfo()
        secret = bytes.fromhex(private_key)
        key_pair = create_new_key_pair(secret)
        peer_id: PeerID = PeerID.from_pubkey(key_pair.public_key)
        print(
            f'Public Key: {key_pair.public_key.serialize().hex()}, PeerId: {peer_id.to_base58()}')
        address = {
            'public_key': key_pair.public_key.serialize().hex(),
            'ip': str(host),
            'port': str(port)
        }

        self.dkg = Dkg(address, private_key, self.node_info,
                       max_workers=0, default_timeout=50)

        self.sa = SA(address, private_key, self.node_info, max_workers=0, default_timeout=50,
                     host=self.dkg.host)
        self.registry_url = registry_url
        self.__nonces: Dict[str, list[Dict]] = {}
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def get_nonces(self, min_number_of_nonces: int = 10, sleep_time: int = 2):
        peer_ids = self.node_info.get_all_nodes()

        # TODO: Random selection
        selected_nodes = {}
        for node_id, peer_ids in peer_ids.items():
            selected_nodes[node_id] = peer_ids[0]

        nonces_response = await self.sa.request_nonces(selected_nodes, min_number_of_nonces)
        self.node_evaluator.evaluate_responses(nonces_response)
        for node_id, peer_id in selected_nodes.items():
            self.__nonces.setdefault(node_id, [])
            if nonces_response[peer_id]['status'] == 'SUCCESSFUL':
                self.__nonces[node_id] += nonces_response[peer_id]['nonces']

    async def update_dkg_list(self) -> None:
        try:
            new_data: Dict = requests.get(self.registry_url).json()
            for id, data in new_data.items():
                self.dkg_list[id] = data
        except Exception as e:
            logging.error(
                f'Registry => Exception occurred: {type(e).__name__}: {e}')

    async def run(self, args) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.dkg.run)
            await self.get_nonces()
            await self.update_dkg_list()
            if args.operation == 'predefined-party':
                party = str(args.party).split(',')
                await self.predefined_party_dkg(args.app_name, args.threshold, party)
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

        nonces_dict = {}
        for node_id in deployment_dkg_key['party'].keys():
            nonces_dict[node_id] = self.__nonces[node_id].pop()
        result = await self.sa.request_signature(deployment_dkg_key, nonces_dict, data, deployment_dkg_key['party'])
        if result['result'] == 'FAILED':
            self.node_evaluator.evaluate_responses(result['signatures'])
            return {
                'status': 'FAILED',
                'sign': result,
                'dkg_response': None
            }
        seed = [i['hash'] for i in result['signatures'].values()][0]
        all_nodes = self.node_info.get_all_nodes()
        new_party = Registry.get_new_random_subset(
            all_nodes, int(seed, 16), n)
        # TODO: Random selection
        selected_nodes = {}
        for node_id, peer_ids in all_nodes.items():
            selected_nodes[node_id] = peer_ids[0]
        new_party = self.node_evaluator.get_new_party(selected_nodes, n)
        is_completed = False
        dkg_response = None
        while not is_completed:
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
                    'seed': seed,
                    'n': n,
                    'dkg_data': dkg_response,
                    'party': new_party,
                    'threshold': threshold,
                },

            }
        }
        nonces_dict = {}
        for node_id in deployment_dkg_key['party'].keys():
            nonces_dict[node_id] = self.__nonces[node_id].pop()
        result = await self.sa.request_signature(deployment_dkg_key, nonces_dict, data, deployment_dkg_key['party'])
        if result['result'] == 'FAILED':
            self.node_evaluator.evaluate_responses(result['signatures'])
            print(json.dumps(result, indent=4))
            return {
                'status': 'FAILED',
                'sign': result,
                'dkg_response': None
            }
        deployment_signature = [i['signature_data']['signature']
                                for i in result['signatures'].values()][0]
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
                'deployment_signature': deployment_signature,
                'timestamp': int(time.time())
            }
        }
        print(json.dumps(res, indent=4))
        return res

    async def predefined_party_dkg(self, app_name: str, threshold: int, party: List):
        # TODO: add log for unsuccessfull DKGs.
        dkg_response = None
        all_nodes = self.node_info.get_all_nodes()

        # TODO: Selected nodes should be random.
        selected_nodes = {}
        for node_id, peer_ids in all_nodes.items():
            selected_nodes[node_id] = peer_ids[0]
        dict_party = {}
        for node_id in party:
            dict_party[str(node_id)] = selected_nodes[str(node_id)]

        dkg_response = await self.dkg.request_dkg(threshold, dict_party, None)
        if dkg_response['dkg_id'] == None:
            return {
                'status': 'FAILED',
                'sign': result,
                'dkg_response': None
            }
        result = dkg_response['result']
        if result == 'SUCCESSFUL':
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
