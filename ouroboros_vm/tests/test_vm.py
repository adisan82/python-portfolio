import unittest
from ouroboros.compiler import Compiler
from ouroboros.vm import VirtualMachine

class TestOuroborosVM(unittest.TestCase):
    def test_addition(self):
        """
        Test code:
        PUSH 10
        PUSH 20
        ADD
        """
        # Safe syntax (no strings with spaces to avoid tokenizer issues)
        source = \"\"\"
        PUSH 10
        PUSH 20
        ADD
        \"\"\"
        
        compiler = Compiler()
        code_obj = compiler.compile(source)
        
        vm = VirtualMachine()
        vm.run(code_obj)
        
        # Result should be on stack: 30
        self.assertEqual(vm.stack[-1], 30)

if __name__ == '__main__':
    unittest.main()
