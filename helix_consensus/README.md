# Helix-Consensus 🧬
> **Distributed Raft Consensus Engine**

**Helix** is a fault-tolerant coordination service implementing the Raft Consensus Algorithm.
It is designed to handle network partitions and ensure strong consistency across a cluster of nodes.

Status: **Leader Election Operational**

---

## 🏛 Architecture

### 1. Network Protocol (`helix/rpc.py`)
- **UDP Transport**: Used for high-frequency Heartbeats.
- **Binary Protocols**: Custom `struct`-packed messages for minimal overhead (19 bytes header).
- **Architecture**: `asyncio.DatagramProtocol`.

### 2. State Machine (`helix/node.py`)
- **Roles**:
  - `FOLLOWER`: Default state. Resets timer on heartbeat.
  - `CANDIDATE`: Triggered by timeout. Increments Term and requests votes.
  - `LEADER`: Elected by Quorum. Broadcasts authority.
- **Safety**: Term-checking ensures stale leaders step down immediately (Split-Brain protection).

### 3. Persistence (`helix/storage.py`)
- **Atomic Writes**: Uses write-rename pattern to save state (`currentTerm`, `votedFor`) to disk.
- **Crash Recovery**: Nodes remember who they voted for after restart to prevent double-voting in the same term.

---

## 🎮 Simulation

Run a 3-node cluster locally in your terminal:

```bash
python simulation.py
```

### Expected Output
```text
[INFO] Node-1: Starting on port 9001 (Term 0)
[INFO] Node-2: Starting on port 9002 (Term 0)
[INFO] Node-3: Starting on port 9003 (Term 0)
[WARN] Node-2: Election Timeout! Becoming CANDIDATE.
[INFO] Node-2: Starting Election (Term 1). Requesting votes...
[INFO] Node-1: Voted FOR Node 2 in term 1
[INFO] Node-3: Voted FOR Node 2 in term 1
[INFO] Node-2: Quorum reached (3 votes). Becoming LEADER!
```

---
*Part of the High-End Engineering Portfolio.*
