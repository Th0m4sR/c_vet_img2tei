import os
import shutil

# Directory paths
vet_directory_log = 'data_directory/logs/vet/'
cvet_directory_log = 'data_directory/logs/cvet/'
directory_warn = 'data_directory/logs/warnings/'
directory_error = 'data_directory/logs/errors/'

# Check if directory paths exist
if not os.path.exists(vet_directory_log) or not os.path.exists(directory_warn):
    print("One of the vet directories doesn't exist.")
    exit()
if not os.path.exists(cvet_directory_log) or not os.path.exists(directory_warn):
    print("One of the cvet directories doesn't exist.")
    exit()

# Iterate through vet_files in vet_directory_log
for filename in os.listdir(vet_directory_log):
    if filename.endswith('.log'):
        log_file_path = os.path.join(vet_directory_log, filename)

        # Check if log file contains 'warning'
        with open(log_file_path, 'r') as file:
            content = file.read()
            if 'warning' in content.lower():
                # Copy log file to directory_warn
                destination_path = os.path.join(directory_warn, filename)
                shutil.copy(log_file_path, destination_path)
                print(f"File '{filename}' copied to directory_warn.")
            if 'error' in content.lower():
                # Copy log file to directory_error
                destination_path = os.path.join(directory_error, filename)
                shutil.copy(log_file_path, destination_path)
                print(f"File '{filename}' copied to directory_error.")

# Iterate through cvet_files in cvet_directory_log
for filename in os.listdir(cvet_directory_log):
    if filename.endswith('.log'):
        log_file_path = os.path.join(cvet_directory_log, filename)

        # Check if log file contains 'warning'
        with open(log_file_path, 'r') as file:
            content = file.read()
            if 'warning' in content.lower():
                # Copy log file to directory_warn
                destination_path = os.path.join(directory_warn, filename)
                shutil.copy(log_file_path, destination_path)
                print(f"File '{filename}' copied to directory_warn.")
            if 'error' in content.lower():
                # Copy log file to directory_error
                destination_path = os.path.join(directory_error, filename)
                shutil.copy(log_file_path, destination_path)
                print(f"File '{filename}' copied to directory_error.")
