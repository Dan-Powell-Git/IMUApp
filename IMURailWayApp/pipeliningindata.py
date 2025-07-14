
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import csv
import os
import json
import pandas as pd
import threading
import queue
import time
import sqlite3
from uuid import uuid4
from google.cloud import storage
from google.oauth2 import service_account

PORT = int(os.environ.get("PORT", 500))

app = Flask(__name__)
SESSION_ID = None
IMU_CSV = "imu_data_log.csv"
RECORDING_FLAG = False
DATA_QUEUE = queue.Queue()
RECORD_COUNT = 0

def check_if_csv_exists():
  expected_header = ['session_id', 'timestamp', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'batch_receive_time']
  if not os.path.exists(IMU_CSV):
    print('No csv path detected, creating one now...')
    with open(IMU_CSV, mode='w', newline='') as file:
      writer = csv.writer(file)
      writer.writerow(expected_header)
      return
  try:
     with open(IMU_CSV, mode='r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
        if header != expected_header:
           print('CSV header is mismatched, recreating csv')
           raise ValueError('Header Mismatch')
  except Exception:
        with open(IMU_CSV, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(expected_header)
        print("CSV recreated with correct header")



def get_storage_client():
   if 'GOOGLE_APP_CREDS_JSON' in os.environ:
      creds_json = os.environ['GOOGLE_APP_CREDS_JSON']
      print('Found Creds!')
      creds_dict = json.loads(creds_json)
      creds = service_account.Credentials.from_service_account_info(creds_dict)
      return storage.Client(credentials=creds)
   else:
      raise EnvironmentError('COULD NOT FIND CREDENTIALS!')
def upload_file(bucket_name, blob_name, local_path):
  try:
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    return print(f'upload to {local_path} completed')
  except Exception as e:
     raise EnvironmentError('Upload Failed!' , str(e))

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
    check_if_csv_exists()
    if not os.path.exists(IMU_CSV):
      return 'No CSV detected'
    df = pd.read_csv(IMU_CSV)
    if df.empty:
      return 'CSV is empty'
    print("Raw columns in CSV:", df.columns.tolist())
    conn = sqlite3.connect(local_DB)
    df.to_sql('imu_data', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

    #upload file with updates back to GCS
    print('Attempting to upload...')
    upload_file(bucket_name, blob_name, local_DB)
    print('Uploaded to GCS')
    #remove local files
    os.remove(IMU_CSV)
    os.remove(local_DB)
    check_if_csv_exists()

    return f'Flushed, uploaded {len(df)} records to GCS'
  except Exception as e:
      return f"Flush failed: {str(e)}"  

def background_writer():
  data_batch = None
  while True:
    try:
        data_batch = DATA_QUEUE.get()
        if data_batch is None:
          break
        check_if_csv_exists()
        print(f"Writing {len(data_batch)} records to CSV")
        with open(IMU_CSV, mode='a', newline='') as file:
          writer = csv.writer(file)
          for row in data_batch:
              writer.writerow([
                SESSION_ID,
                row.get('timestamp'),
                row.get("ax"),
                row.get("ay"),
                row.get("az"),
                row.get("gx"),
                row.get("gy"),
                row.get("gz"),
                row.get('batch_receive_time')])
        try:
          df = pd.read_csv(IMU_CSV, usecols=['timestamp'])  # Load only one column to reduce memory use
          csv_length = len(df)
          print(f'Wrote {len(data_batch)} records to CSV. Total sie of csv is now {csv_length}')
        except Exception as e:
            csv_length = "unknown"
            print("Error reading CSV for size check:", e)
    except Exception as e:
        print("Error in background writer", e)
writer_thread = threading.Thread(target=background_writer, daemon= True)
writer_thread.start()
      

check_if_csv_exists()
        
@app.route("/")
def index():
    return render_template('index.html')

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global RECORDING_FLAG, SESSION_ID
    if RECORDING_FLAG == True:
      return('Already recording...')
    RECORDING_FLAG = True
    SESSION_ID = datetime.now().isoformat()
    return jsonify({'status': 'recording started', 'session_id': SESSION_ID}), 200
  
@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global RECORDING_FLAG
    if RECORDING_FLAG == False:
      print("already not recording.")
    RECORDING_FLAG = False
    print('Waiting for queue to empty')
    while not DATA_QUEUE.empty():
       time.sleep(0.1)

    bucket = 'imu_data_bucket'
    blob = 'imu_data.db'
    msg = flush_csv_to_sqlite(bucket, blob)
    print('Stopped flush', msg)
    return jsonify({'status': 'recording stopped and flushed'}), 200

@app.route('/imu_data', methods = ["POST"]) #Post imu data endpoint
def receive_data():
  global RECORDING_FLAG
  #print(request.get_data())
  data = request.get_json()
  print(f"Incoming Data with {len(data)} records") 
  if not data:
    return jsonify({"Error":"No Data Received"}), 400
  if not isinstance(data, list):
     return jsonify({'Error': f'Data must be list of records\n Data:\n{data}'}, 400)
  if not RECORDING_FLAG:
    print('Not Recording')
    return jsonify({'status': 'queued'}), 200 
  try:
    batch_receive_time = datetime.now().isoformat(timespec='milliseconds')
    for record in data:
       record['batch_receive_time'] =  batch_receive_time
    DATA_QUEUE.put(data)
    return jsonify({'status': 'success', 'count': RECORD_COUNT}), 200
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
@app.route('/record_count')
def get_record_count():
    return jsonify({'count': RECORD_COUNT})