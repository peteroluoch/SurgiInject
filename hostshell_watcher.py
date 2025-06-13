# ghostshell_watcher.py
from hashlib import sha256

class PromptWatcher:
    def __init__(self):
        self.hashes = set()

    def is_duplicate(self, prompt):
        h = sha256(prompt.encode()).hexdigest()
        if h in self.hashes:
            return True
        self.hashes.add(h)
        return False
