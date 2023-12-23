from typing import Dict, List
from config import PENALTY_LIST, DKG_PENALTY_LIST, REMOVE_THRESHOLD
import time
import numpy as np

# TODO: Add node evaluation to database for every command.


class NodePenalty:
    def __init__(self, id: str) -> None:
        self.id = id
        self.__time = 0
        self.__weight = 0

    def add_penalty(self, error_type: str, is_dkg: bool = False) -> None:
        # TODO: handle Data manager.
        self.__time = int(time.time())
        if not is_dkg:
            self.__weight += PENALTY_LIST[error_type]
        else:
            self.__weight += DKG_PENALTY_LIST[error_type]

    def get_score(self) -> int:
        current_time = int(time.time())
        return self.__weight * np.exp(self.__time - current_time)


class NodeEvaluator:
    def __init__(self) -> None:
        self.penalties: Dict[str, NodePenalty] = {}

    def get_new_party(self, old_party: List[str], n: int = None) -> List[str]:
        below_threshold = 0
        for peer_id in old_party:
            if peer_id not in self.penalties.keys():
                self.penalties[peer_id] = NodePenalty(peer_id)
            if self.penalties[peer_id].get_score() < REMOVE_THRESHOLD:
                below_threshold += 1

        score_party = sorted(old_party,
                             key=lambda x: self.penalties[x].get_score(),
                             reverse=True)

        if n is None or n >= len(old_party) - below_threshold:
            n = len(old_party) - below_threshold

        return score_party[:n]

    def evaluate_responses(self, responses: Dict[str, Dict]) -> bool:
        is_complete = True
        guilty_peer_ids = {}
        for peer_id, data in responses.items():
            data_status = data['status']
            guilty_id = None
            if data_status != 'SUCCESSFUL':
                is_complete = False

            if data_status in ['TIMEOUT', 'MALICIOUS']:
                guilty_id = peer_id

            if guilty_id is not None:
                if not self.penalties.get(guilty_id):
                    self.penalties[guilty_id] = NodePenalty(peer_id)
                self.penalties[guilty_id].add_penalty(data_status)
                guilty_peer_ids[guilty_id] = (
                    data_status, self.penalties[guilty_id].get_score())

        return is_complete

    def evaluate_dkg_response(self, result: Dict) -> bool:
        is_complete = True
        guilty_peer_ids = {}
        response: Dict = result['response']
        round1_response = result.get('round1_response', None)
        round2_response = result.get('round2_response', None)
        for peer_id, data in response.items():
            data_status = data['status']
            guilty_id = None
            if data_status != 'SUCCESSFUL':
                is_complete = False

            if data_status == 'COMPLAINT' and round1_response is not None and round2_response is not None:
                # TODO: update exclude complaint
                guilty_id = self.exclude_complaint(
                    data['data'], round1_response, round2_response)

            if data_status in ['TIMEOUT', 'MALICIOUS']:
                guilty_id = peer_id

            if guilty_id is not None:

                if not self.penalties.get(guilty_id):
                    self.penalties[guilty_id] = NodePenalty(peer_id)
                self.penalties[guilty_id].add_penalty(data_status, is_dkg=True)
                guilty_peer_ids[guilty_id] = (
                    data_status, self.penalties[guilty_id].get_score())

        return is_complete
