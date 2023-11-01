#!/bin/python3
import csv
import sys

def convert_time_to_seconds(time_str):
    if 'ms' in time_str:
        return float(time_str.replace(' ms', '')) / 1000
    elif 's' in time_str:
        return float(time_str.replace(' s', ''))
    else:
        return 0

if len(sys.argv) < 2:
    print("Usage: python sort_csv.py <input_csv>")
    sys.exit(1)

input_csv = sys.argv[1]

rows = []
with open(input_csv, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        rows.append(row)

# Sorting by 'triggered' desc, and 'triggered_avg_time' asc
rows.sort(key=lambda x: (-int(x['triggered']), -int(x['unexpected']), convert_time_to_seconds(x['reached_avg_time']), convert_time_to_seconds(x['seeds_avg_time'])))

# Writing the sorted rows back to the CSV
with open(input_csv, 'w', newline='') as csvfile:
    fieldnames = ['config', 'triggered', 'triggered_avg_time', 'reached', 'reached_avg_time', 'unexpected', 'instant', 'seeds_avg_time']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
