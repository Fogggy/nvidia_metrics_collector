import time
import subprocess
import csv
import os
from influxdb import InfluxDBClient
from datetime import datetime
import re
from dotenv import load_dotenv
load_dotenv()


def clear_mbytes(input_string):
    return  input_string.replace(re.sub(r"(\d+[.|,]*\d*)", "", input_string.strip(), 0, re.MULTILINE), "").strip()


def get_nvidia_smi_utilization():
    csv_file_path = f'{os.getcwd()}/tmp/gpu_utilization.csv'

    data = {}

    # write metrics to file
    with open(csv_file_path, 'w') as csvfile:
        subprocess.check_call([
            "/bin/bash",
            "-c",
            "nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv"],
            stdout=csvfile)

    # read metrics
    with open(csv_file_path) as csvfile:
        utilizations = csv.reader(csvfile, delimiter=',')
        counter = 0
        for row in utilizations:
            print(row)
            if counter == 0:
                counter += 1
            else:
                data['utilization.gpu'] = row[0].replace('%', '').strip()
                data['utilization.memory'] = row[1].replace('%', '').strip()
                data['memory.used'] = clear_mbytes(row[2])
                data['memory.total'] = clear_mbytes(row[3])
                data['power.draw'] = row[4].replace('W', '').strip()
    print(data)
    return data


client = InfluxDBClient(os.getenv("INFLUXDB_HOST"),
                        os.getenv("INFLUXDB_PORT"),
                        os.getenv("INFLUXDB_USER"),
                        os.getenv("INFLUXDB_PASSWORD"),
                        os.getenv("INFLUXDB_DATABASE"))
client.create_database(os.getenv("INFLUXDB_DATABASE"))

while True:
    try:
        metrics = get_nvidia_smi_utilization()
        json_body = [
            {
                "measurement": "gpu_usage",
                "time": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "fields": {
                    "utilization_gpu": float(metrics['utilization.gpu']),
                    "utilization_memory": float(metrics['utilization.memory']),
                    "memory_used": int(metrics['memory.used']),
                    "memory_total": int(metrics['memory.total']),
                    "power_draw": float(metrics['power.draw'])
                }
            }
        ]

        client.write_points(json_body)
    except Exception as e:
        print('Error!')
        print(e)
        time.sleep(2)
    time.sleep(.5)
