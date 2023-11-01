#!/bin/python3
import os
import sys
import csv
from datetime import datetime, timedelta

rel_limit = 5

def process_folder(folder_path):
	i=1
	for root, dirs, files in os.walk(folder_path):
		if 'data.out' in files and 'cov.out' in files:
			parts = root.split("/")
			subfolder = parts[parts.index('results') + 1]  # Getting the subfolder name
			# Read data.out
			with open(os.path.join(root, 'data.out'), 'r') as f:
				lines = f.readlines()
				for line in lines:
					if line.startswith("START: "):
						start_time = datetime.strptime(line.split("START: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("SEEDS: "):
						start_time = datetime.strptime(line.split("SEEDS: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("RUN: "):
						start_time = datetime.strptime(line.split("RUN: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("DONE: "):
						end_time = datetime.strptime(line.split("DONE: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("TIMEDOUT: "):
						end_time = datetime.strptime(line.split("TIMEDOUT: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

			# Read and process cov.out
			data = [('0', '0')]
			last_cov = '0'
			cov_index = 1
			if subfolder == 'iban': # Use features for iban
				cov_index = 2
			with open(os.path.join(root, 'cov.out'), 'r') as f:
				lines = f.readlines()
				for line in lines:
					time_str, cov_info = line.split(',')[0], line.split(',')[cov_index]
					time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
					rel_time = (time - start_time).total_seconds()
					if rel_time < 0:
						raise Exception("Negative rel time")
					if rel_limit != None and rel_time >= rel_limit:
						break
					cov = cov_info.split()[1]
					if cov != last_cov:  # Only save when cov changes
						data.append((str(rel_time), cov))
						last_cov = cov

			# Add final entry based on the done time
			final_rel_time = (end_time - start_time).total_seconds()
			if final_rel_time < rel_time:
				print(f"Warning: final rel time < last rel time for {root}")
				print(f"Warning: diff: {rel_time - final_rel_time}")
			else:
				if rel_limit != None and final_rel_time >= rel_limit:
					final_rel_time = rel_limit
				data.append((str(final_rel_time), last_cov))

			# Write to csv
			modified_root = root.replace('../results/', '').replace('_', '-')
			path_parts = modified_root.split('/')
			mid_parts = '-'.join(path_parts[1:-1])
			csv_dir = os.path.join(path_parts[0], mid_parts)
			if rel_limit != None:
				csv_dir = f"{rel_limit}-{csv_dir}"
			csv_filename = f"{i}.csv"
			i+=1

			if not os.path.exists(csv_dir):
				os.makedirs(csv_dir)

			with open(os.path.join(csv_dir, csv_filename), mode='w', newline='') as file:
				writer = csv.writer(file)
				writer.writerow(['time', 'cov'])
				writer.writerows(data)

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("Usage: python script.py <path_to_folder>")
	else:
		folder_path = sys.argv[1]
		if not os.path.exists(folder_path):
			raise Exception("Unknown path")
		process_folder(folder_path)
