# -*- coding: utf-8 -*-
"""
ouroboros.vm
~~~~~~~~~~~~

Silnik Wykonawczy (Runtime Execution Engine).
Iteruje po kodzie bajtowym i manipuluje stosami (Data Stack & Call Stack).
"""

from typing import Any, List
from .opcodes import OpCode, OPCODE_MAP
from .compiler import CodeObject

class VirtualMachine:
    def __init__(self):
        self.stack: List[Any] = []     # Data Stack
        self.globals: dict = {}        # Global Variables
        self.ip: int = 0               # Instruction Pointer
    
    def run(self, co: CodeObject):
        """Główna pętla interpretera."""
        code = co.co_code
        consts = co.co_consts
        names = co.co_names
        
        n = len(code)
        self.ip = 0
        
        print("\n--- VM EXECUTION START ---")
        
        while self.ip < n:
            # 1. Fetch
            op = code[self.ip]
            self.ip += 1
            
            # (Debug Trace)
            # print(f"Exec: {OPCODE_MAP.get(op, '?')} Stack: {self.stack}")
            
            # 2. Decode & Execute
            
            # --- Stack Ops ---
            if op == OpCode.LOAD_CONST:
                idx = self._read_arg(code)
                self.stack.append(consts[idx])
                
            elif op == OpCode.LOAD_NAME:
                idx = self._read_arg(code)
                name = names[idx]
                val = self.globals.get(name)
                if val is None:
                    raise NameError(f"Name '{name}' is not defined")
                self.stack.append(val)
                
            elif op == OpCode.STORE_NAME:
                idx = self._read_arg(code)
                name = names[idx]
                val = self.stack.pop()
                self.globals[name] = val
                
            # --- Arithmetic ---
            elif op == OpCode.ADD:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a + b)
                
            elif op == OpCode.SUB:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a - b)

            elif op == OpCode.MUL:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a * b)
                
            elif op == OpCode.EQ:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a == b)
                
            # --- Control Flow ---
            elif op == OpCode.PRINT:
                val = self.stack.pop()
                print(f"[STDOUT] {val}")
                
            elif op == OpCode.JMP:
                target = self._read_arg(code)
                self.ip = target
                
            elif op == OpCode.JMP_IF_FALSE:
                target = self._read_arg(code)
                condition = self.stack.pop()
                if not condition:
                    self.ip = target
            
            elif op == OpCode.HALT:
                break
                
            else:
                raise RuntimeError(f"Unknown OpCode: {op} at {self.ip}")

        print("--- VM EXECUTION FINISHED ---")

    def _read_arg(self, code: bytearray) -> int:
        """Czyta 16-bit argument (Big Endian) i przesuwa IP."""
        hi = code[self.ip]
        lo = code[self.ip + 1]
        self.ip += 2
        return (hi << 8) | lo
