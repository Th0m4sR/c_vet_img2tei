import os
from schema_validation import SUCCESS_MSG


vet_schema_log_dir = r"data_directory\evaluation\schema_validation_logs\vet"
cvet_schema_log_dir = r"data_directory\evaluation\schema_validation_logs\cvet"


vet_log_paths = [os.path.join(vet_schema_log_dir, log_file) for log_file in os.listdir(vet_schema_log_dir)]
cvet_log_paths = [os.path.join(cvet_schema_log_dir, log_file) for log_file in os.listdir(cvet_schema_log_dir)]

vet_success_count = 0
vet_fail_count = 0
vet_fails = []

cvet_success_count = 0
cvet_fail_count = 0
cvet_fails = []

for filename in vet_log_paths:
    with open(filename, 'r') as file:
        content = file.read()
        if SUCCESS_MSG in content:
            vet_success_count += 1
        else:
            vet_fail_count += 1
            vet_fails.append(os.path.basename(filename))
print(f"{vet_success_count} / {vet_success_count + vet_fail_count} regulations could be validated.")
print("Failed files:")
if len(vet_fails) == 0:
    print("No Fails")
else:
    for vet_fail in vet_fails:
        print(vet_fail)


for filename in cvet_log_paths:
    with open(filename, 'r') as file:
        content = file.read()
        if SUCCESS_MSG in content:
            cvet_success_count += 1
        else:
            cvet_fail_count += 1
            cvet_fails.append(os.path.basename(filename))
print(f"{cvet_success_count} / {cvet_success_count + cvet_fail_count} regulations could be validated.")
print("Failed files:")
if len(cvet_fails) == 0:
    print("No Fails")
else:
    for cvet_fail in cvet_fails:
        print(cvet_fail)
