#!/bin/bash

# Function to run the merge.py script with specified files
run_merge() {
    local dir="$1"
    python3 ./merge.py "$dir/triggered-bugs.csv" "$dir/30-triggered-bugs.csv" "$dir/merged-triggered-bugs.csv"
    echo "Merged files in directory: $dir"
}

# Run the merge function in the current directory
run_merge "."

# Find all subdirectories and run the merge function in each one
find . -mindepth 1 -type d | while read -r dir; do
    run_merge "$dir"
done
