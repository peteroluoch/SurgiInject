"""
Test cases for the SurgiInject injection engine
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.injector import run_injection, validate_code_structure
from engine.prompty import build_prompt, build_simple_prompt, validate_prompt
from engine.diff import get_diff_stats, has_conflicts
from engine.parser import CodeParser
from models.mistral_client import MistralClient, run_model

class TestInjector(unittest.TestCase):
    """Test cases for the injection engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_python_code = '''
def hello_world():
    """A simple function that returns a greeting"""
    return "Hello, World!"

def add_numbers(a, b):
    """Add two numbers together"""
    return a + b

if __name__ == "__main__":
    print(hello_world())
    print(add_numbers(5, 3))
'''.strip()
        
        self.sample_prompt = "Add error handling to the functions to make them more robust."
    
    def test_run_injection_basic(self):
        """Test basic injection functionality"""
        result = run_injection(self.sample_python_code, self.sample_prompt, "test.py")
        
        # Should return a string
        self.assertIsInstance(result, str)
        
        # Should not be empty
        self.assertGreater(len(result), 0)
        
        # Should contain some modification (at minimum, the injected comment)
        self.assertIn("SURGIINJECT", result)
    
    def test_run_injection_empty_code(self):
        """Test injection with empty source code"""
        result = run_injection("", self.sample_prompt, "empty.py")
        
        # Should handle empty code gracefully
        self.assertIsInstance(result, str)
    
    def test_run_injection_empty_prompt(self):
        """Test injection with empty prompt"""
        result = run_injection(self.sample_python_code, "", "test.py")
        
        # Should handle empty prompt gracefully
        self.assertIsInstance(result, str)
    
    def test_validate_code_structure(self):
        """Test code structure validation"""
        # Test with similar sized code
        original = "def test(): pass"
        modified = "def test():\n    # Added comment\n    pass"
        self.assertTrue(validate_code_structure(original, modified))
        
        # Test with empty modified code
        self.assertFalse(validate_code_structure(original, ""))
        
        # Test with massively different sized code
        very_large = "x = 1\n" * 1000
        self.assertFalse(validate_code_structure("x = 1", very_large))

class TestPrompty(unittest.TestCase):
    """Test cases for prompt building"""
    
    def test_build_prompt(self):
        """Test prompt building functionality"""
        code = "def test(): pass"
        task = "Add documentation"
        
        prompt = build_prompt("test.py", code, task)
        
        # Should contain required elements
        self.assertIn("FILE:", prompt)
        self.assertIn("TASK:", prompt)
        self.assertIn("SOURCE CODE:", prompt)
        self.assertIn("INSTRUCTION:", prompt)
        self.assertIn(code, prompt)
        self.assertIn(task, prompt)
    
    def test_build_simple_prompt(self):
        """Test simple prompt building"""
        code = "def test(): pass"
        task = "Add documentation"
        
        prompt = build_simple_prompt(code, task)
        
        # Should contain basic elements
        self.assertIn("SOURCE CODE:", prompt)
        self.assertIn("INSTRUCTION:", prompt)
        self.assertIn(code, prompt)
        self.assertIn(task, prompt)
    
    def test_validate_prompt(self):
        """Test prompt validation"""
        valid_prompt = """
        SOURCE CODE:
        def test(): pass
        
        INSTRUCTION:
        Add documentation to this function.
        """
        
        invalid_prompt = "This is not a valid prompt"
        
        self.assertTrue(validate_prompt(valid_prompt))
        self.assertFalse(validate_prompt(invalid_prompt))
        self.assertFalse(validate_prompt(""))

class TestDiff(unittest.TestCase):
    """Test cases for diff functionality"""
    
    def test_get_diff_stats(self):
        """Test diff statistics calculation"""
        original = "line1\nline2\nline3"
        modified = "line1\nmodified_line2\nline3\nadded_line4"
        
        stats = get_diff_stats(original, modified)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('original_lines', stats)
        self.assertIn('modified_lines', stats)
        self.assertIn('lines_added', stats)
        self.assertIn('lines_removed', stats)
        self.assertEqual(stats['original_lines'], 3)
        self.assertEqual(stats['modified_lines'], 4)
    
    def test_has_conflicts(self):
        """Test conflict detection"""
        original = "line1\nline2\nline3"
        
        # Two modifications that change the same line
        mod1 = "line1\nmodified_line2_v1\nline3"
        mod2 = "line1\nmodified_line2_v2\nline3"
        
        # This is a simplified test - real conflict detection is more complex
        # For now, just test that the function runs without error
        result = has_conflicts(original, mod1, mod2)
        self.assertIsInstance(result, bool)

class TestParser(unittest.TestCase):
    """Test cases for code parsing"""
    
    def test_detect_language(self):
        """Test language detection"""
        parser = CodeParser()
        
        self.assertEqual(parser.detect_language("test.py"), "python")
        self.assertEqual(parser.detect_language("test.js"), "javascript")
        self.assertEqual(parser.detect_language("test.java"), "java")
        self.assertEqual(parser.detect_language("test.unknown"), "unknown")
    
    def test_extract_functions_python(self):
        """Test Python function extraction"""
        parser = CodeParser()
        code = """
def function1():
    pass

def function2(arg1, arg2):
    return arg1 + arg2

class TestClass:
    def method1(self):
        pass
"""
        
        functions = parser.extract_functions(code, "python")
        
        self.assertEqual(len(functions), 3)  # Including method1
        function_names = [f['name'] for f in functions]
        self.assertIn('function1', function_names)
        self.assertIn('function2', function_names)
        self.assertIn('method1', function_names)
    
    def test_extract_classes_python(self):
        """Test Python class extraction"""
        parser = CodeParser()
        code = """
class SimpleClass:
    pass

class InheritedClass(BaseClass):
    def method(self):
        pass
"""
        
        classes = parser.extract_classes(code, "python")
        
        self.assertEqual(len(classes), 2)
        class_names = [c['name'] for c in classes]
        self.assertIn('SimpleClass', class_names)
        self.assertIn('InheritedClass', class_names)
    
    def test_get_code_stats(self):
        """Test code statistics"""
        parser = CodeParser()
        code = """# Comment line
def function():
    pass

# Another comment
x = 1
"""
        
        stats = parser.get_code_stats(code)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_lines', stats)
        self.assertIn('non_empty_lines', stats)
        self.assertIn('comment_lines', stats)
        self.assertGreater(stats['total_lines'], 0)
        self.assertGreater(stats['comment_lines'], 0)

class TestMistralClient(unittest.TestCase):
    """Test cases for Mistral client"""
    
    def test_mock_response(self):
        """Test mock response generation"""
        client = MistralClient()
        
        # Since we're in mock mode by default, this should work
        prompt = """
SOURCE CODE:
def test():
    pass

INSTRUCTION:
Add documentation to this function.
"""
        
        response = client.generate_response(prompt)
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
    
    def test_run_model_function(self):
        """Test the run_model convenience function"""
        prompt = "Test prompt with some code"
        
        response = run_model(prompt)
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""
    
    def test_full_injection_workflow(self):
        """Test the complete injection workflow"""
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as source_file:
            source_file.write('''
def calculate(x, y):
    return x + y

print(calculate(5, 3))
''')
            source_path = source_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as prompt_file:
            prompt_file.write("Add error handling to make the function more robust.")
            prompt_path = prompt_file.name
        
        try:
            # Read the files
            with open(source_path, 'r') as f:
                source_code = f.read()
            
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
            
            # Run injection
            result = run_injection(source_code, prompt_template, source_path)
            
            # Verify result
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            self.assertIn("SURGIINJECT", result)
            
        finally:
            # Clean up temporary files
            os.unlink(source_path)
            os.unlink(prompt_path)

def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestInjector,
        TestPrompty,
        TestDiff,
        TestParser,
        TestMistralClient,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success/failure
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
