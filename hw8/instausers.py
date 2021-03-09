from typing import Dict, Set, List, Optional
from collections import deque
from itertools import cycle
import random
import pickle


class InstaUsers:
    def __init__(self, uri=None):
        self.uri = uri or 'instausers.pkl'  # here: pickle file name
        self.user_db: Dict[int, Dict] = {}
        self.graph: Dict[int, Set[int]] = {}
        self._uid_db: Dict[str, int] = {}  # index by username
        self._mutual: Dict[int, Set[int]] = {}  # only handshakes
        self._parents: Dict[int, Set[int]] = {}  # graph of reversed directions

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def update_db(self, records):
        for record in records:
            uid = record.get('id')
            if uid:
                self.user_db[uid] = record
                username = record.get('username')
                if username:
                    self._uid_db[username] = uid

    def _rebuild_uid_db(self):
        self._uid_db = {}
        for uid, user_data in self.user_db.items():
            username = user_data.get('username')
            if username:
                self._uid_db[username] = uid

    def get_username(self, uid):
        user_data = self.user_db.get(uid, {})
        return user_data.get('username')

    def get_uid(self, username):
        return self._uid_db.get(username)

    def get_user_info(self, uid):
        user_data = self.user_db.get(uid, {})
        return f"{user_data.get('full_name')} ({user_data.get('username')})"

    def update_graph(self, nodes=None):
        if nodes is None:
            nodes = {}
        for node_from, nodes_to in nodes.items():
            if node_from in self.graph:
                self.graph[node_from].update(set(nodes_to))
            else:
                self.graph[node_from] = set(nodes_to)
        self._parents = self.get_parents()
        self._mutual = self.get_mutual_graph()

    def get_parents(self):
        result = {}
        for node_from, nodes_to in self.graph.items():
            for nd_to, nd_from in zip(nodes_to, cycle({node_from})):
                if nd_to not in result:
                    result[nd_to] = set()
                result[nd_to].add(nd_from)
        return result

    def get_mutual_graph(self):
        result = {node_from: nodes_to & self._parents.get(node_from, set())
                  for node_from, nodes_to in self.graph.items()}
        return {node_from: nodes_to
                for node_from, nodes_to in result.items() if nodes_to}

    def get_dpath(self, uid_from, uid_to=None) -> Dict[int, List]:
        return dijkstra(self.graph, start=uid_from, finish=uid_to)

    def get_mutual_dpath(self, uid_from, uid_to=None) -> Dict[int, List]:
        return dijkstra(self._mutual, start=uid_from, finish=uid_to)

    def get_handshake_path(self, username_from, username_to=None) -> List[int]:
        uid_from = self.get_uid(username_from)
        uid_to = self.get_uid(username_to)
        if uid_from is None or uid_to is None:
            return []
        dpath = self.get_mutual_dpath(uid_from, uid_to)
        return dpath.get(uid_to, [])

    def get_next_username(self, usernames) -> Optional[str]:
        """Next username to fetch given endpoints as `usernames`."""
        known_uids = set()
        # Priority 0: unknown users
        for username in usernames:
            uid = self.get_uid(username)
            if uid is None:
                return username
            else:
                known_uids.add(uid)
        if not known_uids:
            return None
        # Priority 1: users on the dead end nodes
        deadends = self.user_db.keys() - self.graph.keys()
        known_deadends = known_uids & deadends
        if known_deadends:
            return self.get_username(known_deadends.pop())
        uidset = known_uids - deadends
        if len(uidset) <= 1:
            return None
        # Priority 2: potential bridges
        bridges = set()
        reachables = {start: set() for start in uidset}
        handshakes = {start: self.get_mutual_dpath(start) or {start: [start]}
                      for start in uidset}
        for finish in deadends:
            parents = self._parents.get(finish, set())
            if len(parents & uidset) > 1:
                return self.get_username(finish)  # direct bridges
            start_matches = []
            path_len = 0
            for start in uidset:
                friends = parents & handshakes[start].keys()
                if friends:
                    start_matches.append(start)
                    path_len += min(
                        len(handshakes[start][friend])
                        for friend in friends
                    ) - 1
            if len(start_matches) > 1:
                bridges.add((finish, path_len))
            else:
                for start in start_matches:
                    reachables[start].add(finish)
        if bridges:
            return self.get_username(sorted(bridges, key=lambda x: x[1])[0][0])
        # Priority 3: random reachable node
        empty_starts = {start for start in reachables if not reachables[start]}
        if empty_starts:
            for start in empty_starts:
                del reachables[start]
        if len(reachables) > 1:
            nodes = []
            weights = []
            common_k = 1 / sum(1 / len(reachables[start])
                               for start in reachables)
            for start in reachables:
                nodes.extend(reachables[start])
                num_nodes = len(reachables[start])
                weights.extend([common_k / num_nodes] * num_nodes)
            chosen = random.choices(nodes, weights)[0]
            return self.get_username(chosen)
        else:
            return None

    def load(self):
        if self.uri:
            try:
                with open(self.uri, 'rb') as file:
                    self.user_db, self.graph = pickle.load(file)
                self.update_graph()
                self._rebuild_uid_db()
            except OSError:
                pass

    def save(self):
        if self.uri:
            try:
                with open(self.uri, 'wb') as file:
                    pickle.dump((self.user_db, self.graph), file)
            except OSError:
                pass


def dijkstra(graph, start, finish=None) -> Dict[int, List]:
    seen = set()
    cost = {start: 0}
    parent = {}
    position = start
    path = {}

    if start not in graph:
        return path
    # Get the cost of reaching end nodes, finish=None means all reachable
    while not (position is None or position == finish):
        seen.add(position)
        for vertex in graph.get(position, set()):
            if vertex not in cost or cost[vertex] > cost[position] + 1:
                cost[vertex] = cost[position] + 1
                parent[vertex] = position
        position = min(cost.keys() - seen, key=lambda x: cost[x], default=None)
    # Restore paths from parent dict
    endpoints = cost.keys() if finish is None else {finish} & cost.keys()
    for endpoint in endpoints:
        way = deque()
        vertex = endpoint
        while vertex != start:
            way.appendleft(vertex)
            vertex = parent.get(vertex)
        else:
            way.appendleft(vertex)
        path[endpoint] = list(way)

    return path
