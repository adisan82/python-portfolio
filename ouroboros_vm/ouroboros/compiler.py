# -*- coding: utf-8 -*-
"""
ouroboros.compiler
~~~~~~~~~~~~~~~~~~

Kompilator języka Ouroboros.
Przetwarza tekst źródłowy na CodeObject (Bytecode + Constants).

Phases:
    1. Tokenizer (Lexical Analysis)
    2. CodeGen (One-pass compiler)
"""

import re
from dataclasses import dataclass
from typing import List, Any, Dict, Tuple
from .opcodes import OpCode

@dataclass
class CodeObject:
    """Skompilowany moduł wykonywalny (jak PyCodeObject)."""
    co_code: bytearray          # Strumień instrukcji
    co_consts: List[Any]        # Tabela stałych (literaly)
    co_names: List[str]         # Tabela nazw (zmienne)

class TokenType:
    IDENTIFIER = 'ID'
    NUMBER     = 'NUM'
    STRING     = 'STR'
    KEYWORD    = 'KW'
    SYMBOL     = 'SYM'

class Compiler:
    def __init__(self):
        self.code = bytearray()
        self.consts = []
        self.names = []
        self.labels = {} # Label -> ByteOffset (dla skoków)
        self.jumps_to_fix = [] # (Offset, LabelName)

    def compile(self, source: str) -> CodeObject:
        """Fasada kompilacji."""
        tokens = self._tokenize(source)
        self._generate(tokens)
        self._fix_jumps()
        return CodeObject(self.code, list(self.consts), list(self.names))

    def _tokenize(self, source: str) -> List[Tuple[str, str]]:
        """Prosty tokenizator."""
        # Usuwanie komentarzy
        lines = source.splitlines()
        clean_lines = [l.split('#')[0].strip() for l in lines if l.strip()]
        
        token_specs = [
            (TokenType.NUMBER, r'\d+'),
            (TokenType.STRING, r'"[^"]*"'),
            (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z0-9_]*'),
            (TokenType.SYMBOL, r'[:;]'),
        ]
        
        tokens = []
        for line in clean_lines:
            # Bardzo proste parsowanie spacjami (Assembler style)
            parts = line.split()
            for part in parts:
                if part.endswith(':'): # Label
                    tokens.append((TokenType.IDENTIFIER, part[:-1]))
                    tokens.append((TokenType.SYMBOL, ':'))
                    continue
                
                # Check specifics
                if part.isdigit():
                    tokens.append((TokenType.NUMBER, part))
                elif part.startswith('"'):
                    tokens.append((TokenType.STRING, part[1:-1]))
                else:
                    tokens.append((TokenType.IDENTIFIER, part))
        return tokens

    def _generate(self, tokens: List[Tuple[str, str]]):
        """Generowanie bytecode."""
        i = 0
        while i < len(tokens):
            typ, val = tokens[i]
            
            # Label definition: "start:"
            if i + 1 < len(tokens) and tokens[i+1][1] == ':':
                self.labels[val] = len(self.code)
                i += 2
                continue

            # Instructions
            if typ == TokenType.IDENTIFIER:
                opcode_name = val.upper()
                
                if hasattr(OpCode, opcode_name):
                    op = getattr(OpCode, opcode_name)
                    self._emit(op)
                    i += 1
                
                # Instrukcje z argumentami (Assembler syntax PUSH 5)
                # Musimy obsłużyć specyficzne mnemoniki
                elif opcode_name == "PUSH":
                    # PUSH 5 -> LOAD_CONST index
                    self._emit(OpCode.LOAD_CONST)
                    arg_typ, arg_val = tokens[i+1]
                    idx = self._add_const(int(arg_val) if arg_typ == TokenType.NUMBER else arg_val)
                    self._emit_arg(idx)
                    i += 2
                
                elif opcode_name == "STORE":
                    self._emit(OpCode.STORE_NAME)
                    arg_typ, arg_val = tokens[i+1]
                    idx = self._add_name(arg_val)
                    self._emit_arg(idx)
                    i += 2
                    
                elif opcode_name == "LOAD":
                    self._emit(OpCode.LOAD_NAME)
                    arg_typ, arg_val = tokens[i+1]
                    idx = self._add_name(arg_val)
                    self._emit_arg(idx)
                    i += 2

                elif opcode_name in ("JMP_IF_FALSE", "JMP"):
                    op_code = getattr(OpCode, opcode_name)
                    self._emit(op_code)
                    target_label = tokens[i+1][1]
                    # Zapisujemy placeholder, naprawimy później
                    self.jumps_to_fix.append((len(self.code), target_label))
                    self._emit_arg(0xFFFF) # Placeholder
                    i += 2
                
                else:
                    # Traktujemy jako implicit instruction bez arg (ADD, PRINT)
                    # Jeśli nie znaleźliśmy w hasattr OpCode, to błąd
                    print(f"Unknown Instruction: {opcode_name}")
                    i += 1
            else:
                i += 1

    def _fix_jumps(self):
        """Backpatching skoków."""
        for offset, label in self.jumps_to_fix:
            if label not in self.labels:
                raise ValueError(f"Undefined label: {label}")
            addr = self.labels[label]
            # Zapisz addr w code[offset : offset+2]
            # Big Endian uint16
            self.code[offset]   = (addr >> 8) & 0xFF
            self.code[offset+1] = addr & 0xFF

    def _emit(self, byte: int):
        self.code.append(byte)

    def _emit_arg(self, arg: int):
        # Args są u nas 16-bitowe (max 65536 stałych)
        self.code.append((arg >> 8) & 0xFF)
        self.code.append(arg & 0xFF)

    def _add_const(self, val: Any) -> int:
        if val in self.consts:
            return self.consts.index(val)
        self.consts.append(val)
        return len(self.consts) - 1

    def _add_name(self, name: str) -> int:
        if name in self.names:
            return self.names.index(name)
        self.names.append(name)
        return len(self.names) - 1
