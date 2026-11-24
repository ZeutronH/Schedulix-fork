import networkx as nx

from sqlalchemy import select

from app.models import CampusNode, CampusEdge, Room


class CampusGraph:

    def __init__(self, db):
        self.db = db
        self.graph = nx.Graph()

    def load(self):
        self.graph.clear()

        nodes = self.db.scalars(
            select(CampusNode)
        ).all()

        edges = self.db.scalars(
            select(CampusEdge)
        ).all()

        for node in nodes:
            self.graph.add_node(
                node.id,
                name=node.name,
                node_type=node.node_type,
                room_id=node.room_id
            )

        for edge in edges:
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                weight=edge.distance,
                connection_type=edge.connection_type,
                accessible=edge.accessible,
                bidirectional=edge.bidirectional
            )

            if not edge.bidirectional:
                # Convert to directed graph when one-way edges exist.
                # The directed representation is constructed below.
                pass

        return self.graph

    def _directed_graph(self, accessible_only=False):
        graph = nx.DiGraph()

        for node, data in self.graph.nodes(data=True):
            graph.add_node(node, **data)

        edges = self.db.scalars(
            select(CampusEdge)
        ).all()

        for edge in edges:
            if accessible_only and not edge.accessible:
                continue

            graph.add_edge(
                edge.source_id,
                edge.target_id,
                weight=edge.distance
            )

            if edge.bidirectional:
                graph.add_edge(
                    edge.target_id,
                    edge.source_id,
                    weight=edge.distance
                )

        return graph

    def shortest_path(
        self,
        source_id,
        target_id,
        accessible_only=False
    ):
        graph = self._directed_graph(accessible_only)

        try:
            path = nx.dijkstra_path(
                graph,
                source_id,
                target_id,
                weight="weight"
            )

            distance = nx.dijkstra_path_length(
                graph,
                source_id,
                target_id,
                weight="weight"
            )

            return {
                "reachable": True,
                "path": path,
                "distance": distance
            }

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "reachable": False,
                "path": [],
                "distance": None
            }

    def nearest_rooms(
        self,
        source_room_id,
        candidate_rooms,
        accessible_only=False
    ):
        graph = self._directed_graph(accessible_only)

        source_nodes = [
            n for n, data in graph.nodes(data=True)
            if data.get("room_id") == source_room_id
        ]

        if not source_nodes:
            return []

        source = source_nodes[0]

        distances = nx.single_source_dijkstra_path_length(
            graph,
            source,
            weight="weight"
        )

        result = []

        for room in candidate_rooms:
            targets = [
                n for n, data in graph.nodes(data=True)
                if data.get("room_id") == room.id
            ]

            if not targets:
                continue

            target = targets[0]

            if target in distances:
                result.append({
                    "room_id": room.id,
                    "distance": distances[target]
                })

        return sorted(result, key=lambda x: x["distance"])