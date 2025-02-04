import sys
import yaml
from collections import defaultdict

# Function to read YAML input from stdin
def read_yaml_from_stdin():
    yaml_input = sys.stdin.read()
    return yaml.safe_load(yaml_input)

# Function to parse and extract resource usage
def parse_resources(experiment_data):
    resource_usage = defaultdict(lambda: defaultdict(lambda: {"requests": {"cpu": 0, "memory": 0}, "limits": {"cpu": 0, "memory": 0}}))
    
    for nodeactor in experiment_data['Experiment']['nodeactors']:
        region = nodeactor['region']
        cluster = nodeactor['cluster']
        replicas = nodeactor['replicas']
        print(f"Processing {nodeactor['name']} in {region}/{cluster} with {replicas} replicas")
        
        for container in nodeactor['containers']:
            # print(f"  Processing container {container['name']}")
            # Safely get the resource data or assign defaults
            resources = container.get('resources', {})
            requests = resources.get('requests', {})
            limits = resources.get('limits', {})
            
            requests_cpu = requests.get('cpu', '0m')
            requests_memory = requests.get('memory', '0M')
            limits_cpu = limits.get('cpu', '0m')
            limits_memory = limits.get('memory', '0M')
            
            # Adjust for the number of replicas
            resource_usage[region][cluster]['requests']['cpu'] += convert_cpu(requests_cpu) * replicas
            resource_usage[region][cluster]['requests']['memory'] += convert_memory(requests_memory) * replicas
            resource_usage[region][cluster]['limits']['cpu'] += convert_cpu(limits_cpu) * replicas
            resource_usage[region][cluster]['limits']['memory'] += convert_memory(limits_memory) * replicas
            # print(f"    {region} - {container['name']} - Requests CPU: {requests_cpu}, Requests Memory: {requests_memory}, Limits CPU: {limits_cpu}, Limits Memory: {limits_memory}")

    return resource_usage

# Function to convert CPU units to milliCPU
def convert_cpu(cpu):
    if cpu.endswith('m'):
        return int(cpu[:-1])
    # elif cpu.endswith('k'):
    #     return int(cpu[:-1]) * 0.001
    # elif cpu.endswith('cpu'):
    #     return int(cpu[:-3]) * 1000
    # elif cpu.isdigit():
    #     return int(cpu) * 1000
    else:
        raise Exception("Invalid CPU unit")

# Function to convert memory units to MiB
def convert_memory(memory):
    if memory.endswith('M'):
        # Throw exception
        return int(memory[:-1])
    else:
        raise Exception(f"Invalid memory unit: {memory}" )

# Read YAML data from stdin
data = read_yaml_from_stdin()

# Get parsed resource usage
resource_usage = parse_resources(data)

# Print results in a table format
print(f"{'Region':<15} {'Device':<10} {'Requests CPU (m)':<20} {'Requests Memory (MiB)':<25} {'Limits CPU (m)':<20} {'Limits Memory (MiB)'}")
for region, clusters in resource_usage.items():
    for cluster, usage in clusters.items():
        print(f"{region:<15} {cluster:<10} {usage['requests']['cpu']:<20} {usage['requests']['memory']:<25} {usage['limits']['cpu']:<20} {usage['limits']['memory']}")


# Define device classes with resource capacities and idle usage
device_classes = {
    "whitebox": {
        "total_cpu": 8000,         # in milliCPU (m)
        "total_memory": 16000,     # in MiB
        "idle_used_cpu": 1000,     # in milliCPU (m)
        "idle_used_memory": 2500   # in MiB
    },
    "rpi4": {
        "total_cpu": 4000,         # in milliCPU (m)
        "total_memory": 4000,      # in MiB
        "idle_used_cpu": 700,      # in milliCPU (m)
        "idle_used_memory": 2000    # in MiB
    }
}

# Mapping device names (regions) to device classes
device_name_to_class = {
    "whx": "whitebox",  # Regions with "whx-mg" map to whitebox
    "rpi": "rpi4"   # Regions with "rpi-region" map to rpi4
}

# Function to classify devices and calculate free resources
def classify_and_calculate_free(device_classes, device_name_to_class, resource_usage):
    free_resources_by_instance = {}
    
    for region, clusters in resource_usage.items():
        # Get device class based on substring match
        device_class = region.split("-")[0]
        device_class = device_name_to_class.get(device_class)
        if not device_class:
            print(f"Warning: Region '{region}' does not have a matching device class. Skipping.")
            continue
        
        specs = device_classes[device_class]
        for cluster, usage in clusters.items():
            used_cpu = specs["idle_used_cpu"] + usage["requests"]["cpu"]
            used_memory = specs["idle_used_memory"] + usage["requests"]["memory"]
            
            free_cpu = max(0, specs["total_cpu"] - used_cpu)
            free_memory = max(0, specs["total_memory"] - used_memory)
            
            free_resources_by_instance[f"{region}/{cluster}"] = {
                "device_class": device_class,
                "free_cpu": free_cpu,
                "free_memory": free_memory
            }
    
    return free_resources_by_instance

# Calculate free resources per instance
free_resources = classify_and_calculate_free(device_classes, device_name_to_class, resource_usage)

# Display results
# Pretty print as table
print("\nFree Resources:")
print(f"{'Instance':<20} {'Device Class':<15} {'Free CPU (m)':<15} {'Free Memory (MiB)'}")
for instance, resources in free_resources.items():
    print(f"{instance:<20} {resources['device_class']:<15} {resources['free_cpu']:<15} {resources['free_memory']}")