import argparse
import subprocess
import os
from pathlib import Path
import ast
import shutil

def extract_parameters_from_protocol(file_path, method_name="add_parameters"):
	with open(file_path, 'r') as file:
		source = file.read()
	tree = ast.parse(source)
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == method_name:
			return ast.get_source_segment(source, node)
	return 'Add parameters method not found.'

Parser = argparse.ArgumentParser()
Parser.add_argument('--file', '-f', type=str, action='store', required=False, help='The path to folder with all scripts to simulate, will default to local "generated_protocols" if not specified')
Parser.add_argument('--labware', '-L', type=str, action='store', required=False, help='Optional path to custom labware definitions')
Parser.add_argument('--output', '-o', type=str, action='store', required=False, help='Absolute Directory to save generated protocol files, will default to local "generated_protocols" if not specified')
Parser.add_argument('--assume_yes', '-y', action='store_true', help='Assume yes for all prompts (e.g., file creation confirmation)')
Parser.add_argument('--silent', '-s', action='store_true', help='Suppress all output except for the final report')
Parser.add_argument('--cleanup-generated', action='store_true', help='After writing the report, delete all files in the simulated protocols folder (e.g. generated_protocols) to avoid duplication on repeated runs')
ParsedArgs = Parser.parse_args()
file = ParsedArgs.file
custom_labware = ParsedArgs.labware
output_dir = ParsedArgs.output
assume_yes = ParsedArgs.assume_yes
silent = ParsedArgs.silent
cleanup_generated = ParsedArgs.cleanup_generated
current_script_dir = os.path.dirname(__file__)
project_root = Path(current_script_dir).parent
report_directory = os.path.join(project_root, "simulation_report.txt") if output_dir is None else output_dir
absolute_protocols_path = os.path.join(project_root, 'generated_protocols') if file is None else file
simulation_raw_directory = Path(os.path.join(project_root,  "simulation_raw_outputs"))
if not silent:
	show_all_results = input("\nPlease enter (y/n) if you would like to display successful results: ").lower().strip() == 'y' if not assume_yes else True
else:
	show_all_results = False
in_memory_module_name = "module"
# If true it will show both successful and failed protocols, default only shows errors.

failure_count = 0
failed_file_names = []
sucessful_file_names = []

print(f"\n--- Generating files in '{simulation_raw_directory}'... ---")
if not simulation_raw_directory.exists():
		simulation_raw_directory.mkdir()
elif len(os.listdir(simulation_raw_directory)) > 0:
	if not assume_yes:
		confirm = input(f"The output directory '{simulation_raw_directory}' is not empty. Do you want to continue and potentially overwrite files? (y/n): ").lower().strip()
		if confirm != 'y':
			print("Operation cancelled by the user.")
			exit(0)
		else:
			print("Continuing with file generation...")
			shutil.rmtree(simulation_raw_directory)  # Clear the directory before generating new files
			simulation_raw_directory.mkdir()  # Recreate the directory after clearing
	else:
		print("Continuing with file generation...")
		shutil.rmtree(simulation_raw_directory)  # Clear the directory before generating new files
		simulation_raw_directory.mkdir()  # Recreate the directory after clearing


print(f"\n--- Starting Simulation of Protocols in '{absolute_protocols_path}'... ---")
for filename in os.listdir(absolute_protocols_path):
	if filename == ".DS_Store":
		continue  # Skip this file
	command = ["opentrons_simulate", filename]
	if custom_labware is not None:
		command.extend(["-L", custom_labware])
	try:
		result = subprocess.run(
			command,
			cwd= absolute_protocols_path,
			capture_output=True,
			text=True,
			check=True  
		)
		#Will only run if the simulation was successful, otherwise it jumps to the except block
		sucessful_file_names.append(filename)
		text = result.stdout
		error = None
		if show_all_results == True:
			print("--- Simulation Successful ---")
			print(filename + "\n")
			print(result.stdout + "\n\n\n")

	except subprocess.CalledProcessError as e:
		# The actual Opentrons error message is in stderr
		if not silent:
			print("\n--- Simulator Error Output (stderr) ---")
			print(filename + "\n")
			print(e.stderr + "\n\n\n")
		failure_count += 1
		failed_file_names.append(filename)
		text = result.stdout
		error = result.stderr

	finally:
		with open(os.path.join(simulation_raw_directory, f"{filename}_simulation_output.txt"), 'w') as f:
			f.write(f"--- Simulation Output for {filename} ---\n\n")
			f.write("Standard Output (stdout):\n")
			f.write(text+"\n")
			f.write("\nStandard Error (stderr):\n")
			f.write(error if error is not None else "No stderr captured.\n")



print(f"\nNumber of failures: {failure_count}")
if not silent:
	view_failed_files = input("Would you like to see which files failed in an ordered list? (y/n): ").lower().strip() == 'y' if not assume_yes else True
else:
	view_failed_files = False
if view_failed_files == True:
	
	def get_numeric_part(filename):
		try:
			
			return int(filename.split('_')[0])
		except (ValueError, IndexError):
			# If it's not a number (like '.DS_Store'), place it at the beginning
			return -1

		# Sort the list using the function as the key
	failed_file_names.sort(key=get_numeric_part)

	print(failed_file_names)
with open(report_directory, 'w') as report_file:
	report_file.write(f"--- Simulation Report ---\n\n")
	report_file.write(f"Total Protocols Simulated: {len(sucessful_file_names) + failure_count}\n")
	report_file.write(f"Successful Simulations: {len(sucessful_file_names)}\n")
	report_file.write(f"Failed Simulations: {failure_count}\n\n")
	if failure_count > 0:
		report_file.write("Failed Protocols:\n")
		for failed in failed_file_names:
			parameter_infromation = extract_parameters_from_protocol(os.path.join(absolute_protocols_path, failed)).split("\n")[1:] # Get everything after the def add_parameters line for better readability
			report_file.write(f"- {failed}\n")
			report_file.write(f"\t  Parameters For Failed Run:\n")
			for line in parameter_infromation:
				report_file.write(f"\t\t{line}\n")

if cleanup_generated and os.path.isdir(absolute_protocols_path):
	shutil.rmtree(absolute_protocols_path)
	Path(absolute_protocols_path).mkdir()
	if not silent:
		print(f"\n--- Cleaned '{absolute_protocols_path}' (--cleanup-generated). ---")