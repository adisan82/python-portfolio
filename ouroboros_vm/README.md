# Ouroboros-VM 🐍
> **Stack-Based Virtual Machine & Compiler built from scratch**

**Ouroboros** is a custom language implementation designed to demonstrate how Python works under the hood. 
It features a complete toolchain: `Source Code -> Lexer -> Compiler -> Bytecode -> VM`.

---

## 🛠 Internals

### 1. Instruction Set (`ouroboros/opcodes.py`)
- Defines the "Machine Code" of Ouroboros.
- Includes stack manipulation (`PUSH`, `POP`), arithmetic (`ADD`, `MUL`), and control flow (`JMP`).

### 2. The Compiler (`ouroboros/compiler.py`)
- **Lexer**: Tokenizes raw text using RegEx.
- **CodeGen**: Single-pass compiler that emits bytecode.
- **Backpatching**: Solves "Jump to Label" problems by reserving bytes and filling addresses later.

### 3. The Execution Engine (`ouroboros/vm.py`)
- Standard **Fetch-Decode-Execute** loop.
- Manages **Data Stack** (for calculations) and **Call Stack** (for functions).
- Implements `LOAD_NAME` / `STORE_NAME` for variable scoping.

---

## 📜 Example Code (`.obs`)

```asm
PUSH 10
STORE x
PUSH 20
LOAD x
ADD
PRINT
```

## 🚀 Running

```bash
python run.py
```

### Output
```text
[STDOUT] 30
[STDOUT] Result is correct!
[STDOUT] Done.
```

---
*The Final Component of the High-End Engineering Portfolio.*
