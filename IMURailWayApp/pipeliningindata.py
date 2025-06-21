
from flask import Flask, request, jsonify
from datetime import datetime
import csv
import os
import json
import pandas as pd
import sqlite3
from uuid import uuid4
from google.cloud import storage
from google.oauth2 import service_account

PORT = int(os.environ.get("PORT", 500))

app = Flask(__name__)
SESSION_ID = None
IMU_CSV = "imu_data_log.csv"
RECORDING_FLAG = False

if not os.path.exists(IMU_CSV): #if the file for the csv does not exist
  with open(IMU_CSV, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['session_id', "timestamp", "ax", "ay", "az", "gx", "gy", "gz"])

def get_storage_client():
   if 'GOOGLE_APP_CREDS_JSON' in os.environ:
      creds_json = os.environ['GOOGLE_APP_CREDS_JSON']
      print('Found Creds!')
      creds_dict = json.loads(creds_json)
      creds = service_account.Credentials.from_service_account_info(creds_dict)
      return storage.Client(credentials=creds)
   else:
      return 'COULD NOT FIND CREDENTIALS!'
def upload_file(bucket_name, blob_name, local_path):
  client = get_storage_client()
  bucket = client.bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.upload_from_filename(local_path)
  return print(f'upload to {local_path} completed')

def download_file(bucket_name, blob_name, local_path):
   client = get_storage_client()
   bucket = client.bucket(bucket_name)
   blob = bucket.blob(blob_name)
   blob.download_to_filename(local_path)
   return print('Downloaded GCS file')
def flush_csv_to_sqlite(bucket_name, blob_name):
  local_DB = 'imu_data.db'
  try:
    download_file(bucket_name, blob_name, local_DB)
    if not os.path.exists(IMU_CSV):
      return 'No CSV detected'
    df = pd.read_csv(IMU_CSV)
    if df.empty():
      return 'CSV is empty'
    conn = sqlite3.connect(local_DB)
    df.to_sql('imu_data', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

    #upload file with updates back to GCS
    upload_file(bucket_name, blob_name, local_DB)

    #remove local files
    os.remove(IMU_CSV)
    os.remove(local_DB)

    return f'Flushed, uploaded {len(df)} records to GCS'
  except Exception as e:
      return f"Flush failed: {str(e)}"  

        
@app.route("/")
def index():
    return '''
    <html>
      <body>
        <h2>IMU Control Panel</h2>
        <form action="/start_recording" method="post"><button>Start</button></form>
        <form action="/stop_recording" method="post"><button>Stop</button></form>
      </body>
    </html>
    '''

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global RECORDING_FLAG, SESSION_ID
    RECORDING_FLAG = True
    SESSION_ID = datetime.utcnow().isoformat()
    return jsonify({'status': 'recording started', 'session_id': SESSION_ID}), 200
  
@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global RECORDING_FLAG
    RECORDING_FLAG = False

    bucket = 'imu_data_bucket'
    blob = 'imu_data.db'
    msg = flush_csv_to_sqlite(bucket, blob)
    print('Stopped flush', msg)
    return jsonify({'status': 'recording stopped and flushed'}), 200

@app.route('/imu_data', methods = ["POST"]) #Post imu data endpoint
def receive_data():
  global RECORDING_FLAG
  print(request.get_data())
  data = request.get_json()
  print("Incoming Data:", data) 
  if not data:
    return jsonify({"Error":"No Data Received"}), 400
  if not RECORDING_FLAG:
    print('Not Recording')
    return jsonify({'status': 'not recording'}), 200 
  try:
        with open(IMU_CSV, mode='a', newline='') as file:
            writer = csv.writer(file)
            for row in data:  # loop through each dictionary in the list
                timestamp = datetime.utcnow().isoformat()
                ax = row.get("ax")
                ay = row.get("ay")
                az = row.get("az")
                gx = row.get("gx")
                gy = row.get("gy")
                gz = row.get("gz")
                writer.writerow([timestamp, ax, ay, az, gx, gy, gz])
        return jsonify({'status': 'success'}), 200
  except Exception as E:
      return jsonify({'Error': str(E)}), 500

@app.route('/flush', methods=['POST'])
def flush():
  bucket = 'imu_data_bucket'
  blob = 'imu_data.db'
  msg = flush_csv_to_sqlite(bucket, blob)
  return (jsonify({'status': msg}))
 
if __name__ == "__main__":
  bucket = 'imu_data_bucket'
  blob = 'imu_data.db'

  app.run(host="0.0.0.0", port=PORT, debug=True)
