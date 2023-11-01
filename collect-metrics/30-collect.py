#!/bin/python3
import os
import csv
from datetime import datetime
import base64
import scipy.stats as stats
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
import statistics
from ztest import two_proportion_ztest

time_limit = 30

sample_size_per_type = (28, 25) # 1: normal sample_size, 2: ft-corrected sample size
sample_size_combined = (3 * sample_size_per_type[0], 3 * sample_size_per_type[1])

keys = ["counts", "timeouts", "times_data"]

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

			with open(os.path.join(root, 'data.out'), 'r') as file:
				lines = file.readlines()
				run_time = None
				for line in lines:
					if line.startswith("START: "):
						run_time = datetime.strptime(line.split("START: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("SEEDS: "):
						run_time = datetime.strptime(line.split("SEEDS: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("RUN: "):
						run_time = datetime.strptime(line.split("RUN: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
					elif line.startswith("DONE: "):
						done_time = datetime.strptime(line.split("DONE: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (done_time - run_time).total_seconds()
						if time_diff < time_limit:
							counts[name] += 1
							times_data[name] += [(time_diff, True)] # Observed value (True)
						else:
							timeouts[name] += 1
							times_data[name] += [(time_limit, False)] # Right-censored (False)

					elif line.startswith("TIMEDOUT: "):
						timeout_time = datetime.strptime(line.split("TIMEDOUT: ")[1].strip(), '%Y-%m-%d %H:%M:%S.%f')

						time_diff = (timeout_time - run_time).total_seconds()

						timeouts[name] += 1
						times_data[name] += [(time_limit, False)] # Right-censored (False)

	return data_dict

def save_only_count_to_csv(sample_size, counts, subfolder='./', csv_filename='30-triggered-bugs.csv'):
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

def save_time_to_csv(times_data, counts, subfolder='./', csv_filename='30-triggered-avg-time.csv', m=1):
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

			if isinstance(p_value, str) or p_value < 0.05:
				hr_val = 'N/A'
				if test_type == "logrank": #and avg_time < inacc_avg_base_time:
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
						ax.get_figure().savefig(os.path.join(subfolder, f"30-survival_curve_{name}.pdf"))

						ax.clear()

				if hr_val != 'N/A' and float(hr_val) < 1:
					name_b = name # Remove bold because its worse
					writer_f.writerow([name, avg_time, median_time, t_stat, p_value, test_type, f"{{\\color{{red}} {hr_val}}}"])
				else:
					writer_f.writerow([name, avg_time, median_time, t_stat, p_value, test_type, hr_val])

			writer.writerow([name_b, avg_time, median_time, t_stat, p_value, test_type])

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
				if key in ['times_data']:
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
		
	data = combine_counts(data_dict)
	save_only_count_to_csv(sample_size_combined, data['counts'])
	save_time_to_csv(data['times_data'], data['counts'])

	check_counts(sample_size_combined, data['counts'], data['timeouts'])
