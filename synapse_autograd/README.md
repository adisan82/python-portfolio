# Synapse-Autograd 🧠
> **Deep Learning Framework internals in Pure Python**

**Synapse** is a pedagogical deep learning engine built from first principles. 
It demonstrates how Automatic Differentiation (Autograd) works under the hood, without relying on `numpy`, `pytorch`, or any external math libraries.

It implements a dynamic Computational Graph (DAG) with Reverse-Mode Differentiation.

---

## 🔬 Core Internals

### 1. The `Tensor` (`synapse/tensor.py`)
- **Internal Storage**: Standard Python Lists (`List[List[float]]`) mimicking 2D Matrices.
- **Operator Overloading**: `+`, `*`, `@` (Example: `z = x @ W + b`) dynamically builds the graph.
- **Closures**: Use of Python closures to store the `backward` pass logic for each operation type (Add, Mul, ReLU).
- **Topology**: Implements `Topological Sort` tolinearize the graph for backpropagation.

### 2. The Math (`synapse/linalg.py`)
- **Pure Python**: Matrix multiplication implemented with triple-nested loops.
- **Optimizations**: Uses `__slots__` memory management to handle thousands of micro-tensors efficiently.

### 3. The Optimizer (`synapse/optim.py`)
- **SGD**: Classic Stochastic Gradient Descent implemented manually.
- **Param Updates**: In-place mutation of tensor data arrays based on accumulated `.grad`.

---

## 🏃 Running the Demo (XOR Problem)

The included demo trains a Multi-Layer Perceptron (MLP) to solve the nonlinear XOR problem.

```bash
python main_training_demo.py
```

### Expected Output
```text
Epoch 0 | Loss: 1.452...
Epoch 50 | Loss: 0.892...
...
Epoch 450 | Loss: 0.012...

Input: [0.0, 0.0] -> Pred: 0.0211
Input: [0.0, 1.0] -> Pred: 0.9823
Input: [1.0, 0.0] -> Pred: 0.9845
Input: [1.0, 1.0] -> Pred: 0.0154
```

---
*Part of the High-End Engineering Portfolio.*
