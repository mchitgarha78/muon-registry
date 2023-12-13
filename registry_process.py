
from muon_frost_py.dkg import DKG
from muon_frost_py.sa.sa import SA
from muon_frost_py.common.utils import Utils
from node_evaluator import NodeEvaluator
from registry_config import REGISTRY_INFO, PRIVATE
from common.node_info import NodeInfo
from common.data_manager import DataManager

from typing import List, Dict
import json
import pprint
import time
import trio
import logging

class RegistryProcess:
    def __init__(self, total_node_number: int, registry_url: str) -> None:
        self.node_info = NodeInfo()
        self.dkg = Dkg(REGISTRY_INFO, PRIVATE, self.node_info, 
                       max_workers=0, default_timeout= 50)
        
        self.sa = SA(REGISTRY_INFO, PRIVATE, self.node_info, max_workers = 0, default_timeout = 50,
                     host = self.dkg.host)
        self.data_manager = DataManager()

        self.total_node_number = total_node_number
        self.registry_url = registry_url
        self.__nonces: Dict[str, list[Dict]] = {} 
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def maintain_nonces(self, min_number_of_nonces: int = 10):
        peer_ids = self.node_info.get_all_nodes(self.total_node_number)
        nonces = await self.sa.request_nonces(peer_ids, min_number_of_nonces * 10)
        self.node_evaluator.evaluate_responses(nonces)
        for peer_id in peer_ids:
            if nonces[peer_id]['status'] == 'SUCCESSFUL':
                self.__nonces.setdefault(peer_id, [])
                self.__nonces[peer_id] += nonces[peer_id]['nonces']

    
    async def update_dkg_list(self):
        new_data: Dict = Utils.get_request(self.registry_url)
        for id, data in new_data.items():
            self.dkg_list[id] = data
    
    async def get_commitments(self, party: List[str], timeout: int = 5) -> Dict:
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
                    "status": "TIMEOUT",
                    "error": "Communication timed out",
                }
                peer_ids_with_timeout[peer_id] = timeout_response
        if len(peer_ids_with_timeout) > 0:
            self.node_evaluator.evaluate_responses(peer_ids_with_timeout)
            logging.warning(f'get_commitments => Timeout error occurred. peer ids with timeout: {peer_ids_with_timeout}')
        return commitments_dict

    async def run(self, args) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.dkg.run)
            await self.maintain_nonces()
            await self.update_dkg_list()
            await self.run_dkg_request(args)
            self.dkg.stop()
            nursery.cancel_scope.cancel()
    
    async def run_dkg_request(self, args):
        threshold = args.threshold
        app_name = args.app_name
        party = json.loads(args.party)
        mode = args.mode
        n = args.node_number
        if mode == 'predefined':
            is_completed = False
            dkg_response = None
            while not is_completed:
                dkg_response = await self.dkg.request_dkg(threshold, party, app_name)
                if dkg_response['dkg_id'] == None:
                    return None
                result = dkg_response['result']                
                if result == 'SUCCESSFUL':
                    is_completed = True
                    res = {
                        dkg_response['dkg_id']:{
                        "app_name": app_name,
                        "threshold": threshold,
                        "party": dkg_response['party'],
                        "public_key": dkg_response['public_key'],
                        "public_shares": dkg_response['public_shares'],
                        "is_predefined": True,
                        "timestamp": int(time.time())
                        }
                    }
                    print(json.dumps(res, indent=4))
                    return res
                else:
                    self.node_evaluator.evaluate_dkg_response(dkg_response)
            
        elif mode == 'random':
            await self.update_dkg_list()
            deployment_app_dkg_id = [key for key, value in self.dkg_list.items() if value['app_name'] == 'deployment_app'][0]
            timestamp = int(time.time()) 
            data = {
                'app': 'deployment_app',
                'method': 'get_random_seed',
                'reqId': Utils.generate_random_uuid(),
                'data': {
                    'params': {
                        'app_name': app_name,
                        'timestamp': timestamp
                    }, 
                }
            }
            commitments_dict = await self.get_commitments(party)
            result = await self.sa.request_signature(self.dkg_list[deployment_app_dkg_id], commitments_dict, data, party)
            print(json.dumps(result, indent=4))
            if result['result'] == 'FAILED':
                self.node_evaluator.evaluate_responses(result['signatures'])
                return result
            all_nodes = self.node_info.get_all_nodes(self.total_node_number)
            new_party = Utils.get_new_random_subset(all_nodes, int(result['message']['signature'], 16), n)
            new_party = self.node_evaluator.get_new_party(new_party, n)
            is_completed = False
            dkg_response = None
            while not is_completed:
                dkg_response = await self.dkg.request_dkg(threshold, new_party, app_name)
                if dkg_response['dkg_id'] == None:
                    return None
                result = dkg_response['result']                
                if result == 'SUCCESSFUL':
                    is_completed = True
                    return dkg_response
                else:
                    self.node_evaluator.evaluate_dkg_response(dkg_response)
            data = {
                'app': 'deployment_app',
                'method': 'verify_dkg_key',
                'reqId': Utils.generate_random_uuid(),
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
            commitments_dict = await self.get_commitments(party)
            result = await self.sa.request_signature(self.dkg_list[deployment_app_dkg_id], commitments_dict, data, party)
            print(json.dumps(result, indent=4))
            if result['result'] == 'FAILED':
                self.node_evaluator.evaluate_responses(result['signatures'])
                print(json.dumps(result, indent=4))
                return result

            res = {
                    dkg_response['dkg_id']:{
                    "app_name": app_name,
                    "threshold": threshold,
                    "party": dkg_response['party'],
                    "public_key": dkg_response['public_key'],
                    "public_shares": dkg_response['public_shares'],
                    "is_predefined": False,
                    "deployment_signature": result['signatures'],
                    "timestamp": int(time.time())
                    }
            }
            print(json.dumps(res, indent=4))

            
