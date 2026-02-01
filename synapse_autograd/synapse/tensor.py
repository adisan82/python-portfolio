# -*- coding: utf-8 -*-
"""
synapse.tensor
~~~~~~~~~~~~~~

Główna klasa `Tensor`.
Reprezentuje węzeł w Grafie Obliczeniowym (Computational Graph).

Autograd Mechanism:
    - Każda operacja (dodawanie, mnożenie) tworzy nowy Tensor.
    - Nowy Tensor zapamiętuje swoich rodziców (`_prev`) oraz operację, która go stworzyła.
    - `backward()` wyzwala łańcuch pochodnych (Chain Rule) w kolejności topologicznej.

Memory Optimization:
    - Używamy `__slots__` dla drastycznej redukcji RAMu przy tysiącach tensorów pośrednich.
"""

import uuid
from typing import List, Set, Tuple, Optional, Union, Callable
from .linalg import Linalg, Matrix

class Tensor:
    __slots__ = ('data', 'grad', '_ctx', '_prev', '_op', 'label', 'requires_grad')

    def __init__(self, data: Union[float, list], _children: Tuple['Tensor', ...] = (), _op: str = '', label: str = ''):
        # Konwersja danych wejściowych na Matrix (List[List[float]]) lub scalar
        # Dla uproszczenia w tym projekcie zakładamy, że wszystko w środku to 2D Matrix (nawet skalary 1x1)
        if isinstance(data, (float, int)):
            self.data = [[float(data)]]
        elif isinstance(data, list) and data and isinstance(data[0], list):
            self.data = data # Już jest Matrix
        elif isinstance(data, list):
            self.data = [data] # Wektor -> Wiersz
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        self.grad: Optional[Matrix] = None # Gradient będzie miał ten sam kształt co data
        
        # Internal Graph State
        self._ctx: Callable = lambda: None # Funkcja wykonująca krok wsteczny (Backprop step)
        self._prev = set(_children) # Rodzice (tensory z których powstaliśmy)
        self._op = _op # Nazwa operacji (dla debugowania grafu)
        self.label = label
        self.requires_grad = True

    def __repr__(self):
        shape = Linalg.shape(self.data)
        return f"Tensor(shape={shape}, op='{self._op}')"

    @property
    def shape(self) -> Tuple[int, int]:
        return Linalg.shape(self.data)

    # --- Operator Overloading ---

    def __add__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        
        # Forward Pass
        out = Tensor(Linalg.add(self.data, other.data), (self, other), '+')

        # Backward Pass Definition (Closure)
        def _backward():
            # Pochodna sumy to 1: d(x+y)/dx = 1 * grad_out
            if self.grad is None: self._init_grad()
            if other.grad is None: other._init_grad()

            # Propagacja gradientu (broadcast handled implicitly or simplified)
            self.grad = Linalg.add(self.grad, out.grad)
            other.grad = Linalg.add(other.grad, out.grad)
            
        out._ctx = _backward
        return out

    def __mul__(self, other):
        """Element-wise multiplication (Hadamard product)."""
        other = other if isinstance(other, Tensor) else Tensor(other)
        
        out = Tensor([[self.data[r][c] * other.data[r][c] 
                       for c in range(len(self.data[0]))] 
                      for r in range(len(self.data))], (self, other), '*')

        def _backward():
            if self.grad is None: self._init_grad()
            if other.grad is None: other._init_grad()
            
            # Chain Rule: d(a*b)/da = b * grad_out
            # Chain Rule: d(a*b)/da = b * grad_out
            # Removed incorrect TODO line
            # W element-wise: grad_self += other.data * out.grad
            
            # Poprawna implementacja element-wise backprop (manual loops)
            rows = len(out.grad)
            cols = len(out.grad[0])
            
            # Calc self grad
            d_self = [[other.data[i][j] * out.grad[i][j] for j in range(cols)] for i in range(rows)]
            self.grad = Linalg.add(self.grad, d_self)
            
            # Calc other grad
            d_other = [[self.data[i][j] * out.grad[i][j] for j in range(cols)] for i in range(rows)]
            other.grad = Linalg.add(other.grad, d_other)

        out._ctx = _backward
        return out

    def matmul(self, other):
        """Matrix Multiplication (Dot Product)."""
        other = other if isinstance(other, Tensor) else Tensor(other)
        
        # Forward
        out = Tensor(Linalg.matmul(self.data, other.data), (self, other), '@')

        def _backward():
            if self.grad is None: self._init_grad()
            if other.grad is None: other._init_grad()
            
            # Gradients for Matrix Mul:
            # Y = A @ B
            # dA = dY @ B.T
            # dB = A.T @ dY
            
            d_self = Linalg.matmul(out.grad, Linalg.transpose(other.data))
            d_other = Linalg.matmul(Linalg.transpose(self.data), out.grad)
            
            self.grad = Linalg.add(self.grad, d_self)
            other.grad = Linalg.add(other.grad, d_other)

        out._ctx = _backward
        return out
    
    def __matmul__(self, other):
        return self.matmul(other)

    def relu(self):
        out = Tensor(Linalg.relu(self.data), (self,), 'ReLU')

        def _backward():
            if self.grad is None: self._init_grad()
            
            # ReLU derivative: 1 if x > 0 else 0
            # grad += (1 if data > 0) * out.grad
            d_relu = Linalg.d_relu(self.data)
            
            # Element-wise mul d_relu * out.grad
            local_grad = [[d_relu[i][j] * out.grad[i][j] 
                           for j in range(len(d_relu[0]))] 
                          for i in range(len(d_relu))]
            
            self.grad = Linalg.add(self.grad, local_grad)

        out._ctx = _backward
        return out

    def sum(self):
        """Redukcja do skalaru (potrzebna jako loss function)."""
        total = Linalg.sum_matrix(self.data)
        out = Tensor(total, (self,), 'Sum')
        
        def _backward():
            if self.grad is None: self._init_grad()
            
            # Gradient sumy to gradient wejściowy rozpropagowany na wszystkie elementy
            # d(sum(x))/dx_i = 1
            # zatem grad_self += 1.0 * out.grad (który jest skalarem 1x1)
            
            grad_val = out.grad[0][0] # Scalar grad from upstream
            rows = len(self.data)
            cols = len(self.data[0])
            
            ones = [[grad_val for _ in range(cols)] for _ in range(rows)]
            self.grad = Linalg.add(self.grad, ones)

        out._ctx = _backward
        return out

    def backward(self):
        """Automatyczne różniczkowanie wsteczne (Topological Sort)."""
        
        # 1. Budowa grafu topologicznego
        topo = []
        visited = set()
        
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        
        build_topo(self)
        
        # 2. Inicjalizacja gradientu wyjściowego (dLoss/dLoss = 1)
        self.grad = [[1.0]]
        
        # 3. Propagacja wsteczna
        for node in reversed(topo):
            node._ctx()

    def _init_grad(self):
        """Lazy intialization zerami."""
        rows = len(self.data)
        cols = len(self.data[0])
        self.grad = Linalg.zeros(rows, cols)
