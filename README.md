# Adisan Scripts
**Core Systems & Distributed Computing Implementations**

This repository contains a collection of five specialized, high-performance systems. Each project is a standalone implementation of complex computer science concepts, built from scratch in pure Python without external heavy dependencies.

---

## 1. Hyperion-Stream: High-Throughput Event Streaming
**Distributed Log-Structured Storage Engine**

Hyperion is a lightweight, high-performance alternative to Apache Kafka, designed for low-latency event streaming. It implements a custom binary protocol and utilizes memory-mapped files for zero-copy data access.

### Core Architecture
- **AsyncIO Network Layer**: (`network/server.py`) Built on Python's `asyncio` reactor pattern handling 10k+ concurrent connections with non-blocking I/O.
- **Write-Ahead Logging (WAL)**: (`storage/wal.py`) Ensures strict durability (ACID) by appending state to disk before acknowledgement, supporting crash recovery.
- **Zero-Copy Serialization**: (`core/protocol.py`) Custom binary protocol using Python `struct` and descriptors for O(1) serialization/deserialization.

### Key Capabilities
- **Partitioned Topic Storage**: Efficient data sharding across logical partitions (`storage/engine.py`).
- **Telemetry & Observability**: Native metric connection and tracing (`utils/telemetry.py`).
- **Crash Recovery**: Automatic log replay mechanism for state restoration.

---

## 2. Nebula-Graph: Distributed Graph Database
**Strongly Consistent Graph Store**

Nebula is a distributed graph database that prioritizes consistency and availability. It serves as a Python-native alternative to Neo4j, featuring a custom query language and efficient traversal algorithms.

### Core Architecture
- **Raft Consensus**: (`cluster/raft.py`) Implements the Raft consensus algorithm for leader election and log replication to ensure strong consistency across the cluster.
- **Adjacency List Storage**: (`core/storage.py`) Optimized storage engine for rapid edge traversal and node retrieval.
- **Inverted Indexing**: (`index/inverted.py`) High-speed property lookups enabling O(1) access to nodes by attributes.

### Key Capabilities
- **GQL Compiler**: (`query/parser.py`) Custom Graph Query Language parser and execution engine.
- **Graph Algorithms**: (`core/algorithms.py`) Built-in support for BFS, DFS, and Shortest Path algorithms.
- **Atomic Primitives**: (`core/primitives.py`) First-class support for Nodes, Edges, and Properties.

---

## 3. Synapse-Autograd: Deep Learning Framework
**Differentiable Programming Engine**

Synapse is a pedagogical yet powerful implementation of a deep learning framework, mirroring the internals of PyTorch. It provides a dynamic computational graph and a fully-featured automatic differentiation engine.

### Core Architecture
- **Reverse-Mode Autodiff**: (`synapse/tensor.py`) Automatic differentiation engine supporting arbitrary dynamic graphs and higher-order derivatives.
- **Dynamic Computational Graph**: nodes are created on-the-fly during forward pass, allowing for complex control flow.
- **Linear Algebra Acceleration**: (`synapse/linalg.py`) Optimized matrix operations and broadcasting rules.

### Key Capabilities
- **Optimizers**: (`synapse/optim.py`) Implementation of stochastic gradient descent (SGD) and other optimization algorithms.
- **Training Pipeline**: (`main_training_demo.py`) Complete training loop infrastructure for neural networks.
- **Tensor Operations**: Comprehensive suite of mathematical operations for tensor manipulation.

---

## 4. Helix-Consensus: Distributed Coordination
**Fault-Tolerant State Machine Replication**

Helix is a coordination service similar to Zookeeper or Etcd, providing primitives for distributed synchronization and configuration management.

### Core Architecture
- **Fault Tolerance**: (`helix/node.py`) Robust leader election and cluster membership protocols handling network partitions and node failures.
- **Hybrid UDP/TCP RPC**: (`helix/rpc.py`) Custom RPC framework optimizing for latency (UDP) and reliability (TCP) where appropriate.
- **Atomic State Persistence**: (`helix/storage.py`) Secure storage of cluster state ensuring correctness across restarts.

### Key Capabilities
- **Network Partition Simulation**: (`simulation.py`) Built-in framework for testing cluster resilience against network faults.
- **Leader Election**: Automated promotion of leader nodes during failures.
- **Watch Mechanisms**: Event-based notifications for state changes.

---

## 5. Ouroboros-VM: Language Virtual Machine
**Custom Stack-Based Execution Engine**

Ouroboros is a complete language implementation featuring a compiler toolchain and a virtual machine, demonstrating the lifecycle of code execution.

### Core Architecture
- **Stack-Based VM**: (`ouroboros/vm.py`) A Fetch-Decode-Execute virtual machine managing data and call stacks for program execution.
- **Compiler Toolchain**: (`ouroboros/compiler.py`) Single-pass compiler transforming source code into executable bytecode.
- **Custom ISA**: (`ouroboros/opcodes.py`) well-defined Instruction Set Architecture optimized for the VM.

### Key Capabilities
- **Regex-Based Lexer**: Efficient tokenization of source logic.
- **Bytecode Execution**: Fast interpretation of compiled instructions.
- **Disassembly**: introspection tools to view generated bytecode.

---

## Engineering Standards

All systems in this repository adhere to production-grade engineering practices:

- **Containerization**: Each project includes a production-optimized `Dockerfile`.
- **Testing**: Comprehensive unit test suites provided in `tests/` directories for each module.
- **Type Safety**: strict type hinting and MyPy compliance.
- **No External Dependencies**: Built entirely with the Python Standard Library to demonstrate core principles.
