import pandas as pd
import json
import time
import csv 


csv_file = "HARdata.csv"

#convert csv data into json
df = pd.read_csv(csv_file)
json_data = df.to_json(orient="records")
print(json_data)

# Open CSV file and read row by row
with open(csv_file, "r") as file:
    reader = csv.reader(file)  # Corrected this line
    header = next(reader)  # Read the header row (optional)

    for row in reader:
        print(", ".join(row))  # Print each row as plain text
        time.sleep(3)  # Wait for 3 seconds
