# -*- coding: utf-8 -*-
"""
Synapse Autograd - XOR Training Demo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstracja możliwości frameworka.
Trenujemy małą sieć neuronową (MLP) do rozwiązania problemu XOR.

Architektura:
    Input (2) -> Hidden (4) + ReLU -> Output (1) -> MSE Loss

Wszystko "from scratch" bez bibliotek zewnętrznych.
"""

import random
from synapse.tensor import Tensor
from synapse.optim import SGD
from synapse.linalg import Linalg

# --- Model Definition ---

class Layer:
    def __init__(self, n_in, n_out):
        # Inicjalizacja wag (Gaussian random)
        self.weights = Tensor(Linalg.randn(n_in, n_out), label="W")
        # Bias (zeros)
        self.bias = Tensor(Linalg.zeros(1, n_out), label="b")

    def __call__(self, x):
        # Forward: x @ W + b
        return x.matmul(self.weights) + self.bias

    def parameters(self):
        return [self.weights, self.bias]

class MLP:
    def __init__(self):
        # 2 input features, 4 hidden neurons
        self.l1 = Layer(2, 4)
        # 4 hidden inputs, 1 output
        self.l2 = Layer(4, 1)

    def __call__(self, x):
        # x -> L1 -> ReLU -> L2
        h = self.l1(x).relu()
        out = self.l2(h)
        return out

    def parameters(self):
        return self.l1.parameters() + self.l2.parameters()

# --- Dataset (XOR) ---

xs = [
    [0.0, 0.0],
    [0.0, 1.0],
    [1.0, 0.0],
    [1.0, 1.0]
]
ys = [
    [0.0],
    [1.0],
    [1.0],
    [0.0]
]

# --- Training Loop ---

def main():
    print("Initializing Synapse Model...")
    model = MLP()
    optimizer = SGD(model.parameters(), lr=0.1)
    
    epochs = 500
    
    print(f"Starting training for {epochs} epochs...")
    
    for epoch in range(epochs):
        # 1. Accumulate Loss
        # Normalnie batching, tu prosty loop
        total_loss = Tensor(0.0)
        
        for x_raw, y_raw in zip(xs, ys):
            # Wrap as Tensors (1x2 matrix for input)
            x = Tensor([x_raw])
            y = Tensor([y_raw])
            
            # Forward
            pred = model(x)
            
            # Loss: (pred - y)^2
            diff = pred + (y * Tensor(-1.0)) # subtraction
            loss = diff * diff # square
            
            total_loss = total_loss + loss.sum()
            
        # 2. Zero Grad
        optimizer.zero_grad()
        
        # 3. Backward
        total_loss.backward()
        
        # 4. Step
        optimizer.step()
        
        if epoch % 50 == 0:
            print(f"Epoch {epoch} | Loss: {total_loss.data[0][0]:.6f}")

    print("\nTraining Complete. Final Predictions:")
    for x_raw in xs:
        x = Tensor([x_raw])
        pred = model(x)
        print(f"Input: {x_raw} -> Pred: {pred.data[0][0]:.4f}")

if __name__ == "__main__":
    main()
