# 🚀 High-Performance Python Engineering Portfolio
> **Principal Engineer / Systems Architect**

This repository contains 5 specialized, high-performance systems integrated into a Monorepo.
Each project demonstrates a specific domain of advanced Computer Science, implemented from scratch in pure Python (No external heavy dependencies).

---

## 📂 Project Index

### 1. [Hyperion-Stream](./hyperion_stream) 🌊
**Distributed Stream Processing Engine**
> *Like a lightweight Kafka/Flink.*
- **Killer Feature**: Custom **Binary Protocol** with Metaclasses & Descriptors.
- **Internals**: `asyncio` Reactor, Write-Ahead-Log (WAL) via `mmap`.

### 2. [Nebula-Graph](./nebula_graph) 🌌
**Distributed Graph Database**
> *Like a Python-native Neo4j.*
- **Killer Feature**: **Raft Consensus Algorithm** and Adjacency List Storage Engine.
- **Internals**: **GQL** (Graph Query Language) Compiler, Inverted Index.

### 3. [Synapse-Autograd](./synapse_autograd) 🧠
**Deep Learning Framework**
> *Like a tiny PyTorch.*
- **Killer Feature**: **Reverse-Mode Automatic Differentiation** engine.
- **Internals**: Dynamic Computational Graph, SGD Optimizer, pure Python Linear Algebra.

### 4. [Helix-Consensus](./helix_consensus) 🧬
**Coordination Service**
> *Like Zookeeper/Etcd.*
- **Killer Feature**: Fault-Tolerant **State Machine Replication**.
- **Internals**: Custom **UDP/TCP Hybrid Protocol**, Atomic State Persistence.

### 5. [Ouroboros-VM](./ouroboros_vm) 🐍
**Language Virtual Machine**
> *A Custom Stack-Based VM.*
- **Killer Feature**: Complete **Compiler Toolchain** (Source -> Lexer -> Bytecode).
- **Internals**: Stack-based execution loop, Call Frames, Instruction Set Architecture (ISA).

---

## 🛠️ DevOps & Infrastructure

Every project is **Cloud-Native Ready**:
- **Dockerized**: Each service has a production-optimized `Dockerfile`.
- **Tested**: Unit test suites included in `tests/` directories.
- **Zero-Dependency**: Runs on standard Python 3.10+.

### Quick Start
```bash
# Example: Run the Deep Learning Demo
cd synapse_autograd
docker build -t synapse .
docker run synapse
```

---

