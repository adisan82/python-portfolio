# -*- coding: utf-8 -*-
"""
hyperion_stream.utils.telemetry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Moduł telemetryczny zgodny ze standardem Prometheus (OpenMetrics).
Kluczowy dla wymagań "Operational Excellence" w systemach AI/ML.

Dlaczego `text-based format`?
- Unikamy ciężkich zależności `prometheus_client`.
- Zerowy narzut przy normalnej pracy (zapis tylko przy scrapowaniu).
- Łatwa integracja z Kubernetes/Sidecarami.

Metryki:
- `hyperion_ops_total`: Licznik operacji (Counter).
- `hyperion_latency_seconds`: Histogram (uproszczony) czasu obsługi.
- `hyperion_wal_size_bytes`: Gauge rozmiaru logu.
- `hyperion_active_connections`: Gauge liczby klientów.
"""

import time
import threading
from typing import Dict, List, Any
from dataclasses import dataclass, field

# Lock dla thread-safety metryk (jeśli używamy Threaded server wrapper w przyszłości)
_METRICS_LOCK = threading.Lock()

@dataclass
class MetricFamily:
    name: str
    type: str
    help_text: str
    samples: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} {self.type}"
        ]
        lines.extend(self.samples)
        return "\n".join(lines) + "\n"

class PrometheusExporter:
    """
    Lekki eksporter metryk.
    Zbiera dane z silnika i formatuje je do 'text/plain'.
    """
    
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        
    def inc_counter(self, name: str, amount: float = 1.0, labels: Dict[str, str] = None):
        """Inkrementacja licznika monotonicznego."""
        key = self._format_key(name, labels)
        with _METRICS_LOCK:
            self._counters[key] = self._counters.get(key, 0.0) + amount

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Ustawienie wartości miernika (może rosnąć/maleć)."""
        key = self._format_key(name, labels)
        with _METRICS_LOCK:
            self._gauges[key] = value

    def _format_key(self, name: str, labels: Dict[str, str]) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f'{name}{{{label_str}}}'

    def generate_metrics(self) -> str:
        """
        Renderuje snapshot metryk.
        Funkcja wywoływana przez end-point HTTP /metrics.
        """
        output = []
        
        # Rendering Counters
        with _METRICS_LOCK:
            for key, val in self._counters.items():
                output.append(f"{key} {val}")
            
            # Rendering Gauges
            for key, val in self._gauges.items():
                output.append(f"{key} {val}")
                
        return "\n".join(output) + "\n"

# Globalna instancja (Singleton w module)
METRICS = PrometheusExporter()
