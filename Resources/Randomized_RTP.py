import importlib.util
import os
import itertools
import pprint
import ast
from pathlib import Path
import argparse
import shutil

class MockParameters:
	"""
	A mock class to capture parameter definitions from a protocol script.
	This mimics the behavior of a real parameter-adding interface.
	"""
	def __init__(self):
		self.added_parameters = []

	def add_bool(self, variable_name, default=None, **kwargs):
		"""Adds a boolean parameter."""
		self.added_parameters.append({"name": variable_name, "type": "bool", "default_value": default, **kwargs})

	def add_int(self, variable_name, default=None, minimum=None, maximum=None, **kwargs):
		"""Adds an integer parameter."""
		self.added_parameters.append({"name": variable_name, "type": "int", "default_value": default, "minimum": minimum, "maximum": maximum, **kwargs})

	def add_str(self, variable_name=None, default=None, choices=None, **kwargs):
		"""Adds a string parameter."""
		self.added_parameters.append({"name": variable_name, "type": "str", "default_value": default, "choices": choices, **kwargs})

	def add_float(self, variable_name, default=None, minimum=None, maximum=None, **kwargs):
		"""Adds a float parameter."""
		self.added_parameters.append({"name": variable_name, "type": "float", "default_value": default, "minimum": minimum, "maximum": maximum, **kwargs})

	def add_csv_file(self, variable_name, default=None, **kwargs):
		"""Adds a CSV file parameter."""
		self.added_parameters.append({"name": variable_name, "type": "csv", "default_value": default, **kwargs})

def generate_combinations(protocol_info):
	"""
	Generates all possible combinations of parameter values based on their
	defined ranges, choices, or boolean states.

	Args:
		protocol_info (dict): A dictionary containing the parameter details.

	Returns:
		list[dict]: A list of dictionaries, where each dictionary represents
					one unique combination of parameter values.
	"""
	parameter_details = protocol_info.get("parameter_details")
	if not parameter_details:
		return []

	# Get the names of the parameters in a fixed order
	param_names = list(parameter_details.keys())
	value_sets = []

	# For each parameter, create a set of interesting values to test
	for name in param_names:
		details = parameter_details[name]
		current_values = set()

		param_type = details.get("type")
		if param_type in ['int', 'float']:
			# Use min, default, and max as the points of interest
			# Use a set to automatically handle duplicates (e.g., if default is same as min)
			if details.get('min') is not None:
				current_values.add(details['min'])
			if details.get('default') is not None:
				current_values.add(details['default'])
			if details.get('max') is not None:
				current_values.add(details['max'])

		elif param_type == 'str' and details.get('choices'):
			# Use all available choices
			for choice in details['choices']:
				current_values.add(choice['value'])

		elif param_type == 'bool':
			# Test both True and False, regardless of the default
			current_values.add(True)
			current_values.add(False)
		
		else:
			# For other types (like csv_file), just use the default value
			if details.get('default') is not None:
				current_values.add(details['default'])

		# If after all checks, there are no values, add None as a placeholder
		if not current_values:
			value_sets.append([details.get('default')])
		else:
			value_sets.append(list(current_values))

	# Calculate the Cartesian product of all value sets
	# This creates all possible combinations
	combinations_tuples = itertools.product(*value_sets)

	# Convert the tuples of values back into dictionaries with parameter names
	combinations_list = [dict(zip(param_names, combo)) for combo in combinations_tuples]

	return combinations_list

class ParameterTransformer(ast.NodeTransformer):
	"""
	This class walks the Abstract Syntax Tree of the Python script and
	modifies the 'default' value in the 'add_*' function calls.
	"""
	def __init__(self, new_defaults: dict):
		self.new_defaults = new_defaults

	def visit_Call(self, node: ast.Call):
		"""Visits every function call in the code."""
		# We are looking for calls to add_int, add_str, etc.
		# These are attribute calls on an object, e.g., `parameters.add_int`
		if isinstance(node.func, ast.Attribute) and node.func.attr.startswith('add_'):
			variable_name = None
			# Find the 'variable_name' argument to identify the parameter
			for keyword in node.keywords:
				if keyword.arg == 'variable_name':
					variable_name = keyword.value.value # ast.Constant stores value in .value
					break
			
			# If this parameter is one we want to change
			if variable_name in self.new_defaults:
				# Find the 'default' argument and change its value
				for keyword in node.keywords:
					if keyword.arg == 'default':
						new_value = self.new_defaults[variable_name]
						# Replace the old value node with a new constant node
						keyword.value = ast.Constant(value=new_value)
						break
		# Continue traversing the rest of the tree
		return self.generic_visit(node)

def modify_script_with_new_defaults(source_code: str, new_defaults: dict) -> str:
	"""
	Parses source code, applies new defaults using an AST transformer,
	and returns the modified source code.
	
	Args:
		source_code (str): The original Python script content.
		new_defaults (dict): The combination of new default values to apply.

	Returns:
		str: The modified Python script content.
	"""
	tree = ast.parse(source_code)
	transformer = ParameterTransformer(new_defaults)
	new_tree = transformer.visit(tree)
	# Fix any missing line numbers/locations for unparsing
	ast.fix_missing_locations(new_tree)
	# Convert the modified tree back to source code
	return ast.unparse(new_tree)


Parser = argparse.ArgumentParser()
Parser.add_argument('--file', '-f', type=str, action='store', required=True, help='The path to the protocol script you want to proces, if a folder then all .py files in that folder will be processed')
Parser.add_argument('--output', '-o', type=str, action='store', required=False, help='Absolute Directory to save generated protocol files, will default to local "generated_protocols" if not specified')
Parser.add_argument('--assume_yes', '-y', action='store_true', help='Assume yes for all prompts (e.g., file creation confirmation)')
ParsedArgs = Parser.parse_args()
file = ParsedArgs.file
output_dir = ParsedArgs.output
assume_yes = ParsedArgs.assume_yes

if __name__ == '__main__': 
	if os.path.isdir(file):
		files = [os.path.join(file, f) for f in os.listdir(file) if f.endswith('.py') and f != '__init__.py']
		absolute_protocols_path = Path(file)
	else:
		files = [file]
		absolute_protocols_path = Path(file).parent
	
	current_script_dir = os.path.dirname(__file__)
	project_root = Path(current_script_dir).parent
	OUTPUT_DIR = project_root / "generated_protocols" # The directory where new protocol files will be saved
	output_dir = OUTPUT_DIR if output_dir == None else Path(output_dir)
	if not output_dir.exists():
		output_dir.mkdir()
	elif len(os.listdir(output_dir)) > 0:
		if not assume_yes:
			confirm = input(f"The output directory '{output_dir}' is not empty. Do you want to continue and potentially overwrite files? (y/n): ").lower().strip()
			if confirm != 'y':
				print("Operation cancelled by the user.")
				exit(0)
			else:
				print("Continuing with file generation...")
				shutil.rmtree(output_dir)  # Clear the directory before generating new files
				output_dir.mkdir()  # Recreate the directory after clearing
		else:
			print("Continuing with file generation...")
			shutil.rmtree(output_dir)  # Clear the directory before generating new files
			output_dir.mkdir()

	# filename = 'AUDIT_AUDIT_AUDIT_AUDIT_Nanopore Genomic Ligation_v5_Final (1).py' <-- In Z_Test

	for filename in files:
		original_filepath = absolute_protocols_path / filename
		if not original_filepath.exists():
			print(f"Error: The file was not found at the specified path: {original_filepath}...skipping.")
			# Exit gracefully if the file doesn't exist.
			continue

		if filename.endswith('.py') and filename != '__init__.py':
				#module_name = filename[:-3]

				 # Give the module a valid in-memory name, e.g., "protocol_module".
				in_memory_module_name = "module"
				spec = importlib.util.spec_from_file_location(in_memory_module_name, original_filepath)

				if not spec or not spec.loader:
					raise ImportError(f"Could not create module spec from file: {original_filepath}")

				module = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(module)


				# full_module_import_path = f"{protocols_directory}.{module_name}"
				#full_module_import_path = f"Archive.{module_name}"


				#module = importlib.import_module(full_module_import_path)

					# Initialize a dictionary to store data for this specific protocol
				current_protocol_info = {"filename": filename}
				if hasattr(module, 'add_parameters') and callable(module.add_parameters):
					mock_params = MockParameters()
					try:
						current_protocol_info = {}
						mock_params = MockParameters()

						module.add_parameters(mock_params)
						# A dictionary to store all details for each parameter
						parameter_details = {}
						for param in mock_params.added_parameters:
							name = param.get("name", "Unnamed")
							parameter_details[name] = {
								"type": param.get("type", "unknown"),
								"default": param.get("default_value"),
								"min": param.get("minimum"),
								"max": param.get("maximum"),
								"choices": param.get("choices")
							}
						current_protocol_info["parameter_details"] = parameter_details

					except Exception as e:
						current_protocol_info["parameters_error"] = f"Error processing parameters: {e}"

		print("-" * 30)
		print(f"Protocol: {filename}")
		print("-" * 30)
		# Printing the details below:
		print("Parameter Details:")
		if "parameter_details" in current_protocol_info:
			for name, details in current_protocol_info["parameter_details"].items():
				# Start building the output string for the current parameter
				output = f"  - {name} ({details['type']}): "

				# Handle string with choices
				if details['type'] == 'str' and details['choices']:
					# Extract the 'display_name' for a cleaner look
					choice_names = [c['display_name'] for c in details['choices']]
					output += f"Default: '{details['default']}', Choices: [{', '.join(choice_names)}]"

				# Handle int/float with min/max values
				elif details['type'] in ['int', 'float']:
					parts = []
					if details['min'] is not None:
						parts.append(f"Min: {details['min']}")
					if details['default'] is not None:
						parts.append(f"Default: {details['default']}")
					if details['max'] is not None:
						parts.append(f"Max: {details['max']}")
					output += ", ".join(parts)


				# Handle bool and other types that only have a default value
				else:
					output += f"Default: {details['default']}"

				print(output)
		elif "parameters_error" in current_protocol_info:
			print(f"  Error: {current_protocol_info['parameters_error']}")

		print("-" * 30) # Seperator


		source_script_content = original_filepath.read_text()

		# --- Generate and print the combinations using the new function ---
		print("\n--- Generated Combinations ---")
		combinations = generate_combinations(current_protocol_info)

		# Pretty print the list of combination dictionaries
		pprint.pprint(combinations,width=120)

		print(f"\nTotal combinations generated: {len(combinations)}")
		print(f"Protocol: {filename}")
		create_combo_files = input("Do you want to create the files for all combinations? (y/n): ").lower().strip() == 'y' if not assume_yes else True
		if create_combo_files == True:
			print(f"\n--- Generating files in '{output_dir}' directory... ---")
			output_dir.mkdir(exist_ok=True) # Create the output directory if it doesn't exist

			for i, combo in enumerate(combinations, 1):
				# Modify the original script content with the new default values
				modified_code = modify_script_with_new_defaults(source_script_content, combo) # Changed

				# Define the new filename (e.g., "1_my_protocol.py")
				new_filename = f"{i}_{Path(filename).name}"
				new_filepath = output_dir / new_filename

				# Write the modified content to the new file
				new_filepath.write_text(modified_code)
				print(f"  Generated: {new_filepath}")

			print("\n--- All files generated successfully! ---")