import unittest
from helix.rpc import Packet, MessageType

class TestHelixRPC(unittest.TestCase):
    def test_packet_serialization(self):
        """Verify pack/unpack integrity."""
        original = Packet(
            msg_type=MessageType.VOTE_REQ,
            term=10,
            src_id=1,
            payload=b"VOTE_FOR_ME"
        )
        
        data = original.pack()
        unpacked = Packet.unpack(data)
        
        self.assertIsNotNone(unpacked)
        self.assertEqual(unpacked.term, 10)
        self.assertEqual(unpacked.msg_type, MessageType.VOTE_REQ)
        self.assertEqual(unpacked.payload, b"VOTE_FOR_ME")

if __name__ == '__main__':
    unittest.main()
