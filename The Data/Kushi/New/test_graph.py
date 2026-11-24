from app.models import CampusNode, CampusEdge
from app.services.graph import CampusGraph


def test_shortest_path(db):
    a = CampusNode(name="A", node_type="BUILDING")
    b = CampusNode(name="B", node_type="JUNCTION")
    c = CampusNode(name="C", node_type="ROOM")

    db.add_all([a, b, c])
    db.flush()

    db.add_all([
        CampusEdge(
            source_id=a.id,
            target_id=b.id,
            distance=10,
            connection_type="CORRIDOR",
            bidirectional=True,
            accessible=True
        ),
        CampusEdge(
            source_id=b.id,
            target_id=c.id,
            distance=15,
            connection_type="CORRIDOR",
            bidirectional=True,
            accessible=True
        ),
        CampusEdge(
            source_id=a.id,
            target_id=c.id,
            distance=100,
            connection_type="OUTDOOR",
            bidirectional=True,
            accessible=True
        )
    ])

    db.commit()

    graph = CampusGraph(db)
    graph.load()

    result = graph.shortest_path(a.id, c.id)

    assert result["reachable"]
    assert result["distance"] == 25


def test_accessibility_routing(db):
    a = CampusNode(name="A", node_type="BUILDING")
    b = CampusNode(name="B", node_type="FLOOR")

    db.add_all([a, b])
    db.flush()

    db.add(
        CampusEdge(
            source_id=a.id,
            target_id=b.id,
            distance=5,
            connection_type="STAIRS",
            bidirectional=True,
            accessible=False
        )
    )

    db.commit()

    graph = CampusGraph(db)
    graph.load()

    result = graph.shortest_path(
        a.id, b.id, accessible_only=True
    )

    assert result["reachable"] is False