#!/usr/bin/env python
"""Sample Python project with intentional issues for pactfix testing."""


def greet(name, items=[]):
    """Greet with mutable default argument (PY003)."""
    items.append(name)
    print("Hello, " + name)
    return items


def check_value(val):
    """Check value with wrong comparison (PY008)."""
    if val is "test":
        return True
    return False


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
