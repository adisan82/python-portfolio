# -*- coding: utf-8 -*-
"""
synapse.optim
~~~~~~~~~~~~~

Optymalizatory gradientowe.
Odpowiedzialne za aktualizację wag tensorów.
"""

from typing import List
from .tensor import Tensor
from .linalg import Linalg

class SGD:
    """
    Stochastic Gradient Descent.
    Wzór: p = p - lr * gradient
    """
    def __init__(self, parameters: List[Tensor], lr: float = 0.01):
        self.parameters = parameters
        self.lr = lr

    def step(self):
        """Wykonuje krok aktualizacji wag."""
        for p in self.parameters:
            if p.grad is None:
                continue
            
            # p.data -= lr * p.grad
            # Musimy pomnożyć gradient przez learning rate
            update_delta = Linalg.mul_scalar(p.grad, self.lr)
            
            # Odejmujemy (Update in-place is tricky with lists substitute, better reassign)
            # p.data = p.data - delta
            p.data = Linalg.sub(p.data, update_delta)

    def zero_grad(self):
        """Zeruje gradienty przed kolejnym krokiem (akumulacja jest domyślna)."""
        for p in self.parameters:
            p.grad = None
