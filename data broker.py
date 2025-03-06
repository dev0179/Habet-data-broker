import pandas as pd
import json

# Define the keys for the JSON object
keys = ["Name", "Latitude", "Longitude", "Altitude", "Temperature", "Pressure", "Humidity", "Garbage"]

def csv_to_json(csv_data):
    # Split the comma-separated values
    values = csv_data.split(',')
    
    # Check if the number of values matches the number of keys
    if len(values) != len(keys):
        raise ValueError(f"Expected {len(keys)} values, but got {len(values)}.")
    
    # Create a dictionary by mapping keys to values
    data_dict = dict(zip(keys, values))
    
    # Convert the dictionary to a JSON object
    json_data = json.dumps(data_dict, indent=4)
    
    return json_data

# Example serial data (comma-separated)
serial_data = "$HAR,12.3456,78.9012,100.5,25.3,1013.25,45.2,ExtraData"

# Convert to JSON
json_object = csv_to_json(serial_data)

# Print the resulting JSON object
print(json_object)

