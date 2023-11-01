#!/bin/python3
import os
import csv
from datetime import datetime
import base64
import scipy.stats as stats
import pandas as pd
from lifelines.statistics import logrank_test
from lifelines import KaplanMeierFitter, CoxPHFitter
import statistics
from ztest import two_proportion_ztest

sample_size_per_type = (28, 25) # 1: normal sample_size, 2: ft-corrected sample size
sample_size_combined = (3 * sample_size_per_type[0], 3 * sample_size_per_type[1])

keys = ["counts", "timeouts", "times_data", "reached", "reached_tdata", "unexpected", "instant", "seeds_tdata"]

def count_lines(directory_path):
	data_dict = {}

	for root, dirs, files in os.walk(directory_path):
		if 'data.out' in files:
			parts = root.split("/")

			subfolder = parts[parts.index('results') + 1]  # Getting the subfolder name
			if subfolder not in data_dict:
				data_dict[subfolder] = {}
				for key in keys:
					data_dict[subfolder][key] = {}

			counts = data_dict[subfolder]['counts']
			timeouts = data_dict[subfolder]['timeouts']
			times_data = data_dict[subfolder]['times_data']
			reached = data_dict[subfolder]['reached']
			reached_tdata = data_dict[subfolder]['reached_tdata']
			unexpected = data_dict[subfolder]['unexpected']
			instant = data_dict[subfolder]['instant']
			seeds_tdata = data_dict[subfolder]['seeds_tdata']
			
			name_index = parts.index('results') + 2
			name = parts[name_index]

			if 'pt' in parts[name_index+1:]:
				name += '-pt'
			elif 'ft' in parts[name_index+1:]:
				name += '-ft'

			name = name.replace("_", "-")

			# Always set all keys
			counts[name] = counts.get(name, 0)
			timeouts[name] = timeouts.get(name, 0)
			times_data[name] = times_data.get(name, [])
			reached[name] = reached.get(name, 0)
			reached_tdata[name] = reached_tdata.get(name, [])
			unexpected[name] = unexpected.get(name, 0)
			instant[name] = instant.get(name, 0)
			seeds_tdata[name] = seeds_tdata.get(name, [])

			with open(os.path.join(root, 'data.out'), 'r') as file:
				lines = file.readlines()
				run_time = None
				reached_time = None
				for line in lines:
					if line.startswith("START: "):
						run_time = datetime.strptime(line.split("START: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("SEEDS: "):
						seed_time = datetime.strptime(line.split("SEEDS: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						if name != "base-corp":
							time_diff = (seed_time - run_time).total_seconds()
							seeds_tdata[name] += [time_diff]

						run_time = seed_time
					elif line.startswith("RUN: "):
						run_time = datetime.strptime(line.split("RUN: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("DONE: "):
						done_time = datetime.strptime(line.split("DONE: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (done_time - run_time).total_seconds()

						counts[name] += 1
						times_data[name] += [(time_diff, True)] # Observed value (True)
					elif line.startswith("TIMEDOUT: "):
						timeout_time = datetime.strptime(line.split("TIMEDOUT: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (timeout_time - run_time).total_seconds()

						timeouts[name] += 1
						times_data[name] += [(time_diff, False)] # Right-censored (False)

						if reached_time == None:
							reached_tdata[name] += [(time_diff, False)]
					elif line.startswith("REACHED: "):
						reached_time_str = line.split("REACHED: ")[1].split(" +")[0][:-3]
						reached_time = datetime.strptime(reached_time_str, '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (reached_time - run_time).total_seconds()

						reached[name] += 1
						reached_tdata[name] += [(time_diff, True)]

			cov_file = os.path.join(root, 'cov.out')
			if os.path.exists(cov_file) and os.path.getsize(cov_file) == 0:
				instant[name] += 1
				if "/ft/diverse_beam_search.json" in root:
					print(f"Warning instant bug in: {root}") # Warn for possible duplicates

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

					break

	return data_dict

def save_only_time_to_csv(times_data, subfolder, csv_filename):
	file_path = os.path.join(subfolder, csv_filename)
	file_path_laptop = os.path.join(subfolder, 'laptop-'+csv_filename)
	file_path_openai = os.path.join(subfolder, 'openai-'+csv_filename)
	with open(file_path, mode='w', newline='') as file, open(file_path_laptop, mode='w', newline='') as file_laptop, open(file_path_openai, mode='w', newline='') as file_openai:
		writer = csv.writer(file)
		writer_laptop = csv.writer(file_laptop)
		writer_openai = csv.writer(file_openai)
		writer.writerow(['Name', 'Average Time', 'Median Time'])
		writer_laptop.writerow(['Name', 'Average Time', 'Median Time'])
		writer_openai.writerow(['Name', 'Average Time', 'Median Time'])
		for name, data in times_data.items():
			if name == 'codegen-350M-multi-ft':
				continue
			if len(data) == 0:
				continue

			avg_time = sum(data) / len(data)
			median_time = statistics.median(data)

			if name.startswith('gpt-'):
				writer_openai.writerow([name, avg_time, median_time])
			elif name == 'codegen-350M-multi-pt' or name == 'codet5p-220m-pt':
				writer_laptop.writerow([name, avg_time, median_time])
			else:
				writer.writerow([name, avg_time, median_time])

def save_time_to_csv(times_data, counts, subfolder='./', csv_filename='triggered-avg-time.csv', m=1):
	test_type = "t-test"
	for _, data in times_data.items():
		for _, observed in data:
			if not observed:
				test_type = "logrank"

	base_times, base_events = zip(*times_data['base'])

	file_path = os.path.join(subfolder, csv_filename)
	file_path_f = os.path.join(subfolder, "filtered-"+csv_filename)
	with open(file_path, mode='w', newline='') as file, open(file_path_f, mode='w', newline='') as file_f:
		writer = csv.writer(file)
		writer_f = csv.writer(file_f)
		writer.writerow(['Name', 'Average Time', 'Median Time', 'Test Statistic', 'P-value', 'Type'])
		writer_f.writerow(['Name', 'Average Time', 'Median Time', 'Test Statistic', 'P-value', 'Type', 'HR'])
		for name, data in times_data.items():
			if counts[name] == 0:
				# avg_time = 'N/A'
				continue

			observed_data = [k*m for (k,v) in data if v]
			avg_time = sum(observed_data) / counts[name]
			median_time = statistics.median(observed_data)

			d_times, d_events = zip(*data)
			if test_type == 't-test':
				t_stat, p_value = stats.ttest_ind(d_times, base_times, equal_var=False)
			else:
				results = logrank_test(d_times, base_times, event_observed_A=d_events, event_observed_B=base_events)
				t_stat, p_value = results.test_statistic, results.p_value

			t_stat = round(t_stat, 3)
			p_value = round(p_value, 3)

			if p_value == 0:
				p_value = '< 0.001'

			name_b = name
			if isinstance(p_value, str) or p_value < 0.05:
				name_b = f"{{\\bf{{{name}}}}}"

			if isinstance(p_value, str) or p_value < 0.05 or (subfolder == './' and (name == 'starcoderplus-pt' or name == 'codegen-16B-multi-pt')):
				hr_val = 'N/A'
				if test_type == "logrank": #and avg_time < inacc_avg_base_time:
					# if name == 'codet5p-16b-pt':
					# 	d_times = [x + 128.734 for x in d_times]

					# Plot survival curve
					kmf = KaplanMeierFitter()

					# Fitting data for the base group
					kmf.fit(base_times, event_observed=base_events, label='base')
					ax = kmf.plot()

					# Fitting and plotting for the current group
					kmf.fit(d_times, event_observed=d_events, label=name)
					ax = kmf.plot(ax=ax)

					# Adding labels and title
					if subfolder != './':
						ax.set_title(subfolder)
					ax.set_xlabel('Time in seconds')
					ax.set_ylabel('Survival function')
					ax.legend()

					# Calculate Hazard Ratio
					data = pd.concat([
						pd.DataFrame({
							'duration': d_times,
							'event': d_events,
							'group': 'treatment'
						}),
						pd.DataFrame({
							'duration': base_times,
							'event': base_events,
							'group': 'control'
						}),
					])
					data['group'] = (data['group'] == 'treatment').astype(int)
					cph = CoxPHFitter()
					cph.fit(data, duration_col='duration', event_col='event')
					hr_val = f"{round(cph.hazard_ratios_.iloc[0], 3):.3f}"

					ax.text(x=0.98, y=0.8, s=f"HR = {hr_val}", transform=ax.transAxes, ha="right")

					# Saving the plot
					ax.get_figure().savefig(os.path.join(subfolder, f"survival_curve_{name}.pdf"))

					ax.clear()

				if hr_val != 'N/A' and float(hr_val) < 1:
					name_b = name # Remove bold because its worse
					writer_f.writerow([name, avg_time, median_time, t_stat, p_value, test_type, f"{{\\color{{red}} {hr_val}}}"])
				else:
					writer_f.writerow([name, avg_time, median_time, t_stat, p_value, test_type, hr_val])

			writer.writerow([name_b, avg_time, median_time, t_stat, p_value, test_type])

def save_reached_to_csv(reached, reached_tdata, data_dict, csv_filename='reached.csv'):
	with open(csv_filename, mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['name', 'reached', 'time', 'clean_html_reached', 'clean_html_time', 'iban_reached', 'iban_time', 'saml_reached', 'saml_time'])  # Writing the header
		for name in reached:
			count, time = get_reached_data(name, sample_size_combined, reached, reached_tdata)
			clean_html_reached, clean_html_time = get_reached_data(name, sample_size_per_type, data_dict['clean_html']['reached'], data_dict['clean_html']['reached_tdata'])
			iban_reached, iban_time = iban = get_reached_data(name, sample_size_per_type, data_dict['iban']['reached'], data_dict['iban']['reached_tdata'])
			saml_reached, saml_time = get_reached_data(name, sample_size_per_type, data_dict['saml']['reached'], data_dict['saml']['reached_tdata'])
			writer.writerow([name, count, time, clean_html_reached, clean_html_time, iban_reached, iban_time, saml_reached, saml_time])

def save_only_count_to_csv(sample_size, counts, subfolder='./', csv_filename='triggered-bugs.csv'):
	file_path = os.path.join(subfolder, csv_filename)
	base_count, base_samples = counts['base'], get_sample_size('base', sample_size)
	with open(file_path, mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['Name', 'Perc'])
		for name, count in counts.items():
			samples = get_sample_size(name, sample_size)
			perc = int(round(count/samples*100, 0))

			z_score, p_value = two_proportion_ztest(base_count, base_samples, count, samples)
			if p_value < 0.05 and z_score < 0:
				name = f"{{\\bf{{{name}}}}}"

			writer.writerow([name, perc])

def get_reached_data(name, sample_size, reached, reached_tdata):
	perc = int(round(reached[name]/get_sample_size(name, sample_size)*100, 0))

	observed_data = [k for (k,v) in reached_tdata[name] if v]
	if reached[name] == 0:
		avg_time = 'N/A'
	else:
		avg_time = round(sum(observed_data)/reached[name]*1000)

	return f"{perc}\\%", f"{avg_time} ms"

def check_counts(sample_size, counts, timeouts):
	for name in counts:
		total = counts[name] + timeouts[name]
		if total != get_sample_size(name, sample_size):
			raise Exception(f" Missing result for {name}, the total of DONE and TIMEDOUT is {total}, not sample size {sample_size}.")

def combine_counts(data_dict):
	combined = {}
	for key in keys:
		combined[key] = {}

	for subfolder, data in data_dict.items():
		for key in keys:
			for name, value in data[key].items():
				if key in ['times_data', 'reached_tdata', 'seeds_tdata']:
					combined[key][name] = combined[key].get(name, []) + value
				else:
					combined[key][name] = combined[key].get(name, 0) + value

	return combined

def get_sample_size(name: str, sample_size):
	if name.endswith("-ft"):
		return sample_size[1]
	return sample_size[0]

if __name__ == "__main__":
	directory_path = '../results/'
	data_dict = count_lines(directory_path)

	for subfolder, data in data_dict.items():
		os.makedirs(subfolder, exist_ok=True)  # Ensure the subfolder exists

		save_only_count_to_csv(sample_size_per_type, data['counts'], subfolder)
		save_time_to_csv(data['times_data'], data['counts'], subfolder)
		check_counts(sample_size_per_type, data['counts'], data['timeouts'])

		save_time_to_csv(data['reached_tdata'], data['reached'], subfolder, csv_filename='reached-avg-time.csv', m=1000)

		if subfolder != "saml":
			save_only_count_to_csv(sample_size_per_type, data['unexpected'], subfolder, csv_filename='unexpected-bugs.csv')

		save_only_count_to_csv(sample_size_per_type, data['instant'], subfolder, csv_filename='instant-bugs.csv')

		save_only_time_to_csv(data['seeds_tdata'], subfolder, csv_filename='seed-times.csv')

	data = combine_counts(data_dict)
	save_only_count_to_csv(sample_size_combined, data['counts'])
	save_time_to_csv(data['times_data'], data['counts'])

	save_reached_to_csv(data['reached'], data['reached_tdata'], data_dict)

	save_only_count_to_csv(sample_size_combined, data['unexpected'], csv_filename='unexpected-bugs.csv')

	save_only_count_to_csv(sample_size_combined, data['instant'], csv_filename='instant-bugs.csv')

	save_only_time_to_csv(data['seeds_tdata'], './', csv_filename='seed-times.csv')

	check_counts(sample_size_combined, data['counts'], data['timeouts'])
