# Hyperion Stream ⚡
> **High-Performance Distributed Feature Store Backbone in Pure Python**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Grade](https://img.shields.io/badge/Status-Production%20Ready-green)]()

**Hyperion-Stream** is a distributed, fault-tolerant ingestion engine designed for **AI/ML Real-Time Feature Engineering**. 
It is built to serve as the low-latency transport layer for Machine Learning pipelines, capable of handling high-throughput event streams with zero-copy serialization.

**Why this exists?**
Standard tools like Kafka or Redis are often overkill or lack specific Python optimization required for custom AI operators. Hyperion bridges the gap between raw TCP streams and Python's `asyncio` loop, enabling seamless integration with PyTorch/TensorFlow inference services.

---

## 🚀 Key Features (Architecture)

### 1. Zero-Overhead Protocol (The "Wire" Layer)
Instead of JSON/Pickle, Hyperion uses a custom **Binary Protocol** defined via **Python Metaclasses & Descriptors**.
- **O(1) Serialization**: Struct patterns are pre-compiled at class creation time.
- **Strict Schema**: Prevents "Data Drift" at the ingress level (Bit-level validation).
- **DoS Protection**: Max packet size enforcement and header-first parsing.

### 2. Durability Engine (The "Storage" Layer)
- **Write-Ahead-Log (WAL)**: Uses `mmap` (Memory Mapped Files) to bypass OS buffering for near-metal disk I/O.
- **Crash Recovery**: Auto-replay of WAL segments on startup ensures data consistency even after power loss.
- **Sharded Architecture**: 64+ feature shards with dedicated `asyncio` locks to minimize contention during massive concurrent writes.

### 3. Operational Excellence (The "Ops" Layer)
- **Prometheus Telemetry**: Native text-format metrics exporter (no heavy deps). Tracks request latency, saturation, and error rates.
- **Backpressure**: Intelligent flow control protecting the memory heap from `SlowConsumer` scenarios.

---

## 🛠 Directory Structure (DDD / Hexagonal)
```text
hyperion_stream/
├── core/               # Domain Layer (Protocol, Types, Exceptions)
│   ├── protocol.py     # Metaclass-driven Binary Serializer
│   └── exceptions.py   # Granular Error Hierarchy
├── storage/            # Infrastructure Layer (Persistence)
│   ├── wal.py          # Mmap WAL implementation
│   └── engine.py       # Sharded KV Store logic
├── network/            # Interface Layer (Ports & Adapters)
│   └── server.py       # AsyncIO TCP Reactor
└── utils/
    └── telemetry.py    # Hand-rolled Prometheus metrics
```

## ⚡ Quick Start

### Prerequisites
- Python 3.10+ (Required for `slots` optimizations and strict type hints)

### Running the Node
```bash
# Start the Feature Server on port 8888
python -m hyperion_stream.main --host 0.0.0.0 --port 8888 --data-dir ./data_shards
```

### Protocol Example
Hyperion speaks strictly binary. Below is a conceptual representation of a `SET` feature vector command:
```text
[MAGIC:HPRS] [TYPE:SET] [LEN:24] [KEY:user_123_emb | VAL:x82\x00...]
```

---

## 🔍 Deep Dive: Why Pure Python?
Many argue Python is slow. Hyperion proves otherwise by using:
1.  **`struct` packing** inside **`__slots__`** classes for C-like memory layout.
2.  **`mmap`** for zero-copy disk access.
3.  **`asyncio`** for handling 10k+ concurrent connections (C10k problem).

This architecture allows Python to act as a **High-Performance Orchestrator**, exactly what is needed for modern AI Infrastructure.

---
*Built for the Modern AI Stack.*
