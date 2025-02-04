import os
import sys
import numpy as np
import argparse
import logging
import tarfile
import shutil
import subprocess
logger = logging.getLogger()
from tqdm import tqdm
import pandas as pd

temp_dir=".tmp_exp_analyzer"

def read_csv_files(directory):
    data = []

    df_list = []

    # Walk through all subdirectories and files
    for root, _, files in os.walk(directory):
        csv_files = [file for file in files if file.endswith('.csv')]
        logger.debug(csv_files)
        for file in tqdm(csv_files, desc="Processing CSV files"):
            file_path = os.path.join(root, file)
            df = pd.read_csv(file_path, index_col=False)
            df_list.append(df)
            with open(file_path, 'r') as f:
                lines = f.readlines()[1:]  # Ignore the first line (headers)
                cleaned_lines = []
                for line in lines:
                    columns = line.split(',')
                    if len(columns) >= 2:  # Ensure at least two columns exist
                        cleaned_lines.append(','.join(columns[:2]))  # Use only the first two columns
                try:
                    csv_data = np.genfromtxt(cleaned_lines, delimiter=',', dtype=float)
                    data.append(csv_data)
                except ValueError as e:
                    logger.error(f"Error parsing {file_path}: {e}")
    
    # Save the merged dataframes to a single csv file
    df = pd.concat(df_list)
    df.to_csv("merged_data.csv", index=False)
    return data

def extract_experiment_data(expfile, temp_dir):    
    # Step 1: Create the temporary directory
    os.makedirs(temp_dir, exist_ok=True)
    
    # Step 2: Extract the experiment file
    logger.info(f"Extracting {expfile}")
    with tarfile.open(expfile, "r:gz") as tar:
        tar.extractall(temp_dir, members=(m for m in tar if "client" in m.name))
    logger.debug(f"Contents of {temp_dir}:")
    logger.debug(os.listdir(temp_dir))
    logger.info(f"Extracted {expfile}")
    
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".tar"):
                tar_path = os.path.join(root, file)
                with tarfile.open(tar_path, "r") as tar:
                    tar.extractall()
                
                client_delay_csv = "app/results/client_delay.csv"
                if os.path.exists(client_delay_csv):
                    new_csv_name = f"{tar_path}.csv"
                    os.rename(client_delay_csv, new_csv_name)
                
                # Clean up the extracted app directory
                if os.path.exists("app"):
                    shutil.rmtree("app")

def cleanup_experiment_data(temp_dir):
    shutil.rmtree(temp_dir)


    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read CSV files from a directory')
    parser.add_argument('experiment_file', type=str, help='File containing the experiment data (tar.gz)')

    parser.add_argument('-a', '--attack', type=int, help='Attack time in seconds')
    parser.add_argument('-p', '--postattack', type=int, help='Post time in seconds')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(levelname)s - %(message)s')
    if args.debug:
        logger.setLevel(logging.DEBUG)

    extract_experiment_data(args.experiment_file, temp_dir)

    csv_data = read_csv_files(temp_dir)

    # Separate the date of each csv in three groups. The first is the lines where the time (second column) if less than 60, thhe second group is between 60 and 180 and the third is above 180

    group1_list = []
    group2_list = []
    group3_list = []

    preattack = args.attack
    postattack = args.postattack
    group1_errors = 0
    group2_errors = 0
    group3_errors = 0
    for data in csv_data:
        if len(data) == 0:
            continue
                
        group1 = data[data[:, 0] < preattack]
        group2 = data[(data[:, 0] >= preattack) & (data[:, 0] < postattack)]
        group3 = data[data[:, 0] >= postattack]
        
        group1_list += list(group1[:, 1])        
        group2_list += list(group2[:, 1])
        group3_list += list(group3[:, 1])

        group1_errors += np.isnan(group1_list).sum()
        group2_errors += np.isnan(group2_list).sum()
        group3_errors += np.isnan(group3_list).sum()

        # Drop nan values
        group1_list = [x for x in group1_list if str(x) != 'nan']
        group2_list = [x for x in group2_list if str(x) != 'nan']
        group3_list = [x for x in group3_list if str(x) != 'nan']

    # Calculate the mean of each group
    group1_mean = np.mean(group1_list, axis=0)
    group2_mean = np.mean(group2_list, axis=0)
    group3_mean = np.mean(group3_list, axis=0)

    # get the number of NAN values in group2
    logger.info(f'Average time for client response (Before {preattack} seconds)    : {group1_mean:.3f} - {group1_errors} errors')
    logger.info(f'Average time for client response ({preattack} - {postattack} seconds)      : {group2_mean:.3f} - {group2_errors} errors')
    logger.info(f'Average time for client response (After {postattack} seconds)     : {group3_mean:.3f} - {group3_errors} errors')

    cleanup_experiment_data(temp_dir)
