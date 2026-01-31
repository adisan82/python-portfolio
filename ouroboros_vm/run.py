# -*- coding: utf-8 -*-
"""
run.py
~~~~~~

Entry point for Ouroboros VM.
Loads source -> Compiles -> Runs.
"""

import sys
from ouroboros.compiler import Compiler
from ouroboros.vm import VirtualMachine
from ouroboros.opcodes import disassemble

def main():
    source_file = "example_script.obs"
    
    print(f"Loading {source_file}...")
    with open(source_file, "r") as f:
        source = f.read()

    # 1. Compile
    print("Compiling...")
    compiler = Compiler()
    code_obj = compiler.compile(source)
    
    print(f"Bytecode size: {len(code_obj.co_code)} bytes")
    print(f"Consts: {code_obj.co_consts}")
    print(f"Names: {code_obj.co_names}")
    
    # 2. Disassemble (Debug)
    disassemble(code_obj.co_code)
    
    # 3. Execute
    vm = VirtualMachine()
    vm.run(code_obj)

if __name__ == "__main__":
    main()
