import unittest
from nebula_graph.core.storage import GraphStorage

class TestGraphStorage(unittest.TestCase):
    def setUp(self):
        self.store = GraphStorage()

    def test_add_node(self):
        """Test adding and retrieving a node."""
        node = self.store.add_node(labels=["User"], name="TestUser")
        retrieved = self.store.get_node(node.id)
        
        self.assertEqual(node.id, retrieved.id)
        self.assertEqual(retrieved.properties['name'], "TestUser")
        self.assertIn("User", retrieved.labels)

    def test_add_edge(self):
        """Test connecting two nodes."""
        n1 = self.store.add_node(name="A")
        n2 = self.store.add_node(name="B")
        edge = self.store.add_edge(n1.id, n2.id, "LINKS_TO")
        
        self.assertEqual(edge.src, n1.id)
        self.assertEqual(edge.dst, n2.id)
        self.assertEqual(edge.type, "LINKS_TO")

if __name__ == '__main__':
    unittest.main()
