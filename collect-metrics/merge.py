import csv
import sys

def merge_csv(file1, file2, output_file):
    merged_data = []
    
    # Read the first CSV file and store it in a dictionary
    with open(file1, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        for row in reader:
            name, perc = row
            merged_data.append({'Name': name, 'Perc': int(perc)})
            
    # Read the second CSV file and update the dictionary
    with open(file2, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        for row in reader:
            name, perc_30 = row
            for data in merged_data:
                if data['Name'] == name or data['Name'] == f"{{\\bf{{{name}}}}}" or f"{{\\bf{{{data['Name']}}}}}" == name:
                    data['30 Perc'] = int(perc_30)
                    data['Name'] = name
            
    # Sort the merged data by '30 Perc' and 'Perc'
    merged_data.sort(key=lambda x: (x['30 Perc'], x['Perc']))
    
    # Write the sorted, merged data into a new CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['Name', 'Perc', '30 Perc'])
        writer.writeheader()
        writer.writerows(merged_data)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: ./merge.py <file1.csv> <file2.csv> <output_file.csv>")
    else:
        merge_csv(sys.argv[1], sys.argv[2], sys.argv[3])
        print(f"Merged and sorted data written to {sys.argv[3]}")
