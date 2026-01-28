#!/usr/bin/env python3
import os
import sys
import json

def process_data(items=[]):
    for item in items:
        if item == None:
            print "Item is None"
            continue
        try:
            result = item * 2
        except:
            print "Error processing item"
    return items

def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

if __name__ == "__main__":
    data = [1, 2, None, 4]
    process_data(data)
    
    if len(sys.argv) == None:
        print "No arguments"
