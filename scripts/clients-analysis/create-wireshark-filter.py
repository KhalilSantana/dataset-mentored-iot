#!/usr/bin/env python3
# Create a filter with ip.addr=={x}||ip.addr=={y}||ip.addr=={z} where {x}, {y}, and {z} are the IP addresses of the hosts matching a prefix

import sys

#main
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 create-wireshark-filter.py <prefix>")
        sys.exit(1)

    prefix = sys.argv[1] 
    hosts_file =  sys.argv[2] if len(sys.argv) > 2 else "etc_hosts.txt"
    
    # Filter for the IP addresses of the hosts matching the prefix
    filter = ""
    with open(hosts_file, 'r') as f:
        for line in f:
            ip_address, hostname = line.split()
            if hostname.startswith(prefix):
                filter += f"ip.addr=={ip_address}||"
    filter = filter.rstrip("||")
    print(filter)