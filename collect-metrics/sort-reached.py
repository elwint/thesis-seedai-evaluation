#!/bin/python3
import csv

def sort_csv(input_file_path, output_file_path):
    # Reading the data from the csv file
    with open(input_file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)  # Skipping the header row
        rows = [row for row in reader]
        
    # Sorting the rows
    # First, by the 'reached' column in descending order
    # Then, by the 'time' column in ascending order
    rows.sort(key=lambda x: (-int(x[1].replace('\\', '').strip('%')), int(x[2].strip(' ms'))))
    
    # Writing the sorted data back to a csv file
    with open(output_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)  # Writing the header row
        writer.writerows(rows)

sort_csv('reached.csv', 'reached.csv')
