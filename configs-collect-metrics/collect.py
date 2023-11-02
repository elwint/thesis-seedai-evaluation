#!/bin/python3
import sys
import os
import csv
from datetime import datetime
import base64

configs = ['diverse_beam_search.json', 'temp_0.2.json', 'temp_0.6.json', 'temp_0.8.json', 'top_p_0.50.json', 'top_p_0.75.json', 'top_p_0.99.json']
sample_size = 3*4

pt_configs = ['code.json', 'code_multi.json', 'text.json', 'text_multi.json']
pt_sample_size = 7*3

def count_lines(directory_path, model_path):
	counts = {}
	timeouts = {}
	time_sums = {}
	reached = {}
	reached_tsums = {}
	unexpected = {}
	instant = {}
	seeds_tsums = {}
	has_pt = False

	for root, dirs, files in os.walk(directory_path):
		if 'data.out' in files:
			parts = root.split("/")
			if model_path not in root:
				continue
			index = parts[-1].find(".json")
			if index == -1:
				raise Exception(f"No config dir result in {root}")
			name = parts[-1][:index+5]

			pt_name = False
			if "pt" in parts:
				pt_index = parts[-1].find(".json_")
				if index == -1:
					raise Exception(f"No PT config dir result in {root}")
				pt_name = parts[-1][pt_index+6:]
				has_pt=True

			# Always set all keys
			counts[name] = counts.get(name, 0)
			timeouts[name] = timeouts.get(name, 0)
			time_sums[name] = time_sums.get(name, 0)
			reached[name] = reached.get(name, 0)
			reached_tsums[name] = reached_tsums.get(name, 0)
			unexpected[name] = unexpected.get(name, 0)
			instant[name] = instant.get(name, 0)
			seeds_tsums[name] = seeds_tsums.get(name, 0)
			if pt_name:
				counts[pt_name] = counts.get(pt_name, 0)
				timeouts[pt_name] = timeouts.get(pt_name, 0)
				time_sums[pt_name] = time_sums.get(pt_name, 0)
				reached[pt_name] = reached.get(pt_name, 0)
				reached_tsums[pt_name] = reached_tsums.get(pt_name, 0)
				unexpected[pt_name] = unexpected.get(pt_name, 0)
				instant[pt_name] = instant.get(pt_name, 0)
				seeds_tsums[pt_name] = seeds_tsums.get(pt_name, 0)

			with open(os.path.join(root, 'data.out'), 'r') as file:
				lines = file.readlines()
				run_time = None
				for line in lines:
					if line.startswith("START: "):
						run_time = datetime.strptime(line.split("START: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("SEEDS: "):
						seed_time = datetime.strptime(line.split("SEEDS: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (seed_time - run_time).total_seconds()
						seeds_tsums[name] += time_diff
						if pt_name:
							seeds_tsums[pt_name] += time_diff

						run_time = seed_time
					elif line.startswith("RUN: "):
						run_time = datetime.strptime(line.split("RUN: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("DONE: "):
						done_time = datetime.strptime(line.split("DONE: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (done_time - run_time).total_seconds()

						counts[name] += 1
						time_sums[name] += time_diff
						if pt_name:
							counts[pt_name] += 1
							time_sums[pt_name] += time_diff
					elif line.startswith("TIMEDOUT: "):
						timeouts[name] += 1
						if pt_name:
							timeouts[pt_name] += 1
					elif line.startswith("REACHED: "):
						reached_time_str = line.split("REACHED: ")[1].split(" +")[0][:-3]
						reached_time = datetime.strptime(reached_time_str, '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (reached_time - run_time).total_seconds()

						reached[name] += 1
						reached_tsums[name] += time_diff
						if pt_name:
							reached[pt_name] += 1
							reached_tsums[pt_name] += time_diff

			cov_file = os.path.join(root, 'cov.out')
			if os.path.exists(cov_file) and os.path.getsize(cov_file) == 0:
				instant[name] += 1
				if pt_name:
					instant[pt_name] += 1

			subfolder = parts[parts.index('results') + 1]  # Getting the subfolder name
			if subfolder == 'clean_html':
				expected = ['<<', '>>', '&lt;', '&gt;']
			elif subfolder == 'iban':
				expected = ['-', '+']
			else:
				continue

			log_file = os.path.join(root, 'log.out')
			if not os.path.exists(log_file):
				continue

			with open(log_file, 'r') as file:
				lines = file.readlines()
				for i, line in enumerate(lines):
					if not "Base64:" in line:
						continue

					encoded_str = line.split(' ')[-1].strip()  # Extracts the base64 encoded string
					decoded_bytes = base64.b64decode(encoded_str)
					decoded_str = decoded_bytes.decode('utf-8', errors='surrogateescape')

					found = False
					for e in expected:
						if e in decoded_str:
							found = True
							break

					if not found:
						unexpected[name] += 1
						if pt_name:
							unexpected[pt_name] += 1

					break

	return counts, timeouts, time_sums, reached, reached_tsums, unexpected, instant, seeds_tsums, has_pt

def save_config_to_csv(configs, sz, config_counts, config_time_sums, config_reached, config_reached_tsums, unexpected, instant, seeds_tsums, csv_filename='config-data.csv'):
	with open(csv_filename, mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['config', 'triggered', 'triggered_avg_time', 'reached', 'reached_avg_time', 'unexpected', 'instant', 'seeds_avg_time'])  # Writing the header
		for config in configs:
			if config_counts[config] == 0:
				triggered_avg_time = 'N/A'
			else:
				triggered_avg_time = round(config_time_sums[config] / config_counts[config], 2)

			sample_size = sz
			# if config == 'diverse_beam_search.json':
			# 	sample_size = 3

			reached_perc = 100
			if config_reached[config] != sample_size:
				reached_perc = round(config_reached[config]/sample_size*100, 3)

			if config_reached[config] == 0:
				reached_avg_time = 'N/A'
			else:
				reached_avg_time = round(config_reached_tsums[config] / config_reached[config] * 1000)

			seeds_avg_time =  round(seeds_tsums[config] / sample_size, 2)

			writer.writerow([config.replace("_", "\\_"), config_counts[config], f"{triggered_avg_time} s", f"{reached_perc}\\%", f"{reached_avg_time} ms", unexpected[config], instant[config], f"{seeds_avg_time} s"])

def check_counts(configs, sz, counts, timeouts):
	for config in configs:

		sample_size = sz
		# if config == 'diverse_beam_search.json':
		# 	sample_size = 3

		total = counts[config] + timeouts[config]
		if total != sample_size:
			raise Exception(f"Missing result for {config}, the total of DONE and TIMEDOUT is {total}, not sample size {sample_size}.")

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("Usage: python script.py <model_name>/<ft/pt>")
		exit(1)

	directory_path = '../results/'
	counts, timeouts, time_sums, reached, reached_tsums, unexpected, instant, seeds_tsums, has_pt = count_lines(directory_path, sys.argv[1])

	file_name = sys.argv[1].replace("/", "-")

	save_config_to_csv(configs, sample_size, counts, time_sums, reached, reached_tsums, unexpected, instant, seeds_tsums, f"configs-{file_name}.csv")
	check_counts(configs, sample_size, counts, timeouts)
	if has_pt:
		save_config_to_csv(pt_configs, pt_sample_size, counts, time_sums, reached, reached_tsums, unexpected, instant, seeds_tsums, f"pt-configs-{file_name}.csv")
		check_counts(pt_configs, pt_sample_size, counts, timeouts)
