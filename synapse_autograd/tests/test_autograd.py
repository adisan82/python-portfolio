import unittest
from synapse.tensor import Tensor

class TestAutograd(unittest.TestCase):
    def test_simple_gradient(self):
        """
        Test derivative of z = x * y
        x = 2, y = 3 -> z = 6
        dz/dx = y = 3
        """
        x = Tensor(2.0)
        y = Tensor(3.0)
        z = x * y
        
        z.backward()
        
        # Check gradient data
        # Data is stored as [[val]]
        grad_x = x.grad[0][0]
        self.assertEqual(grad_x, 3.0)

    def test_add_grad(self):
        """
        z = x + x
        dz/dx = 2
        """
        x = Tensor(5.0)
        z = x + x
        z.backward()
        
        self.assertEqual(x.grad[0][0], 2.0)

if __name__ == '__main__':
    unittest.main()
