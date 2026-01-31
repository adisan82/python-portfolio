# High-Performance Python Engineering Portfolio
**Principal Engineer / Systems Architect**

This repository contains five specialized, high-performance systems integrated into a Monorepo. Each project demonstrates a specific domain of advanced Computer Science, implemented from scratch in pure Python without external heavy dependencies.

---

## Project Index

### 1. [Hyperion-Stream](./hyperion_stream)
**Distributed Stream Processing Engine**
*A lightweight alternative to Kafka/Flink.*

- **Key Features**: Custom Binary Protocol using Metaclasses & Descriptors for O(1) serialization.
- **Technical Implementation**: Built on `asyncio` Reactor pattern with a Write-Ahead-Log (WAL) using memory-mapped files (`mmap`) for durability.

### 2. [Nebula-Graph](./nebula_graph)
**Distributed Graph Database**
*A Python-native alternative to Neo4j.*

- **Key Features**: Strong consistency via Raft Consensus Algorithm and an Adjacency List Storage Engine.
- **Technical Implementation**: Custom GQL (Graph Query Language) Compiler and Inverted Indexing for efficient property lookups.

### 3. [Synapse-Autograd](./synapse_autograd)
**Deep Learning Framework**
*A pedagogical implementation of PyTorch internals.*

- **Key Features**: Reverse-Mode Automatic Differentiation engine supporting arbitrary dynamic graphs.
- **Technical Implementation**: Dynamic Computational Graph construction, SGD Optimizer, and pure Python Linear Algebra utilities.

### 4. [Helix-Consensus](./helix_consensus)
**Coordination Service**
*A distributed coordination service similar to Zookeeper or Etcd.*

- **Key Features**: Fault-Tolerant State Machine Replication handling network partitions.
- **Technical Implementation**: Hybrid UDP/TCP Protocol design and Atomic State Persistence to handle crash recovery.

### 5. [Ouroboros-VM](./ouroboros_vm)
**Language Virtual Machine**
*A custom Stack-Based Virtual Machine.*

- **Key Features**: Complete Compiler Toolchain taking source code to executable bytecode.
- **Technical Implementation**: Regex-based Lexer, Single-pass Compiler, and a Fetch-Decode-Execute VM loop managing Data and Call Stacks.

---

## DevOps & Infrastructure

All projects are designed for Cloud-Native environments:

- **Containerization**: Each service includes a production-optimized `Dockerfile`.
- **Testing**: Comprehensive unit test suites provided in `tests/` directories for each module.
- **Compatibility**: Compatible with standard Python 3.11+.

### Quick Start

To run the Deep Learning demonstration:

```bash
cd synapse_autograd
docker build -t synapse .
docker run synapse
```
