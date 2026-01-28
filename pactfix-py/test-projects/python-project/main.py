#!/usr/bin/env python3
"""Sample Python project with intentional issues for pactfix testing."""

import os

def greet(name, items=[]):
    """Greet with mutable default argument (PY003)."""
    items.append(name)
    # pactfix: Dodano nawiasy do print() (was: print "Hello, " + name)
    print("Hello, " + name)
    return items

def check_value(val):
    """Check value with wrong comparison (PY004)."""
    if val == None:
        return False
    return True

def process_data():
    """Process with bare except (PY002)."""
    try:
        data = open("data.txt").read()
        return data
    except:
        return None

if __name__ == "__main__":
    greet("World")
    check_value(None)
