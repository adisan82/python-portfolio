# -*- coding: utf-8 -*-
"""
synapse.linalg
~~~~~~~~~~~~~~

Biblioteka algebry liniowej w czystym Pythonie.
Zastępuje NumPy dla celów edukacyjnych/inżynierskich, operując na natywnych listach.

Performance Note:
    - O(N^3) dla naiwnego mnożenia macierzy.
    - Brak wektoryzacji SIMD (ograniczenie CPython).
    - Używamy list comprehensions dla "szybkości" na poziomie interpretera.
"""

import math
import random
from typing import List, Union, Tuple

# Typy pomocnicze
Vector = List[float]
Matrix = List[List[float]]
TensorData = Union[float, Vector, Matrix]

class Linalg:
    """
    Statyczna klasa z narzędziami matematycznymi.
    Unikamy tworzenia instancji, traktuj to jako namespace.
    """

    @staticmethod
    def matmul(a: Matrix, b: Matrix) -> Matrix:
        """
        Mnożenie macierzy A (MxK) * B (KxN) -> C (MxN).
        Implementacja naiwna (Triple Loop).
        """
        rows_a = len(a)
        cols_a = len(a[0])
        rows_b = len(b)
        cols_b = len(b[0])

        if cols_a != rows_b:
            raise ValueError(f"Shape mismatch: ({rows_a},{cols_a}) vs ({rows_b},{cols_b})")

        # Pre-alokacja zerami
        result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]

        for i in range(rows_a):
            for j in range(cols_b):
                acc = 0.0
                for k in range(cols_a):
                    acc += a[i][k] * b[k][j]
                result[i][j] = acc
        
        return result

    @staticmethod
    def add(a: Matrix, b: Matrix) -> Matrix:
        """Element-wise addition."""
        rows = len(a)
        cols = len(a[0])
        return [[a[i][j] + b[i][j] for j in range(cols)] for i in range(rows)]

    @staticmethod
    def sub(a: Matrix, b: Matrix) -> Matrix:
        """Element-wise subtraction."""
        rows = len(a)
        cols = len(a[0])
        return [[a[i][j] - b[i][j] for j in range(cols)] for i in range(rows)]

    @staticmethod
    def mul_scalar(a: Matrix, scalar: float) -> Matrix:
        """Mnożenie macierzy przez skalar."""
        return [[val * scalar for val in row] for row in a]

    @staticmethod
    def transpose(a: Matrix) -> Matrix:
        """Transpozycja macierzy (A.T)."""
        rows = len(a)
        cols = len(a[0])
        return [[a[j][i] for j in range(rows)] for i in range(cols)]

    @staticmethod
    def relu(a: Matrix) -> Matrix:
        """Rectified Linear Unit: max(0, x)."""
        return [[max(0.0, val) for val in row] for row in a]

    @staticmethod
    def d_relu(a: Matrix) -> Matrix:
        """Pochodna ReLU (1.0 dla x>0, 0.0 dla x<=0)."""
        return [[1.0 if val > 0 else 0.0 for val in row] for row in a]

    @staticmethod
    def sum_matrix(a: Matrix) -> float:
        """Redukcja macierzy do skalaru (suma wszystkich elementów)."""
        total = 0.0
        for row in a:
            total += sum(row)
        return total

    @staticmethod
    def randn(rows: int, cols: int) -> Matrix:
        """Inicjalizacja losowa (rozkład normalny Gaussa)."""
        return [[random.gauss(0.0, 1.0) for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def zeros(rows: int, cols: int) -> Matrix:
        return [[0.0 for _ in range(cols)] for _ in range(rows)]
    
    @staticmethod
    def shape(a: TensorData) -> Tuple[int, ...]:
        """Rekursywne sprawdzanie kształtu (dla 2D max)."""
        if isinstance(a, float) or isinstance(a, int):
            return ()
        if not a:
            return (0,)
        if isinstance(a[0], list):
            return (len(a), len(a[0]))
        return (len(a),)
