
from flask import Flask, request, jsonify
from datetime import datetime
import csv
import os
PORT = int(os.environ.get("PORT", 500))

app = Flask(__name__)

IMU_CSV = "imu_data_log.csv"
RECORDING_FLAG = False

if not os.path.exists(IMU_CSV): #if the file for the csv does not exist
  with open(IMU_CSV, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["timestamp", "ax", "ay", "az", "gx", "gy", "gz"])

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
    global RECORDING_FLAG
    RECORDING_FLAG = True
    return jsonify({'status': 'recording started'}), 200
  
@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global RECORDING_FLAG
    RECORDING_FLAG = False
    return jsonify({'status': 'recording stopped'}), 200

@app.route('/imu_data', methods = ["POST"]) #Post imu data endpoint
def receive_data():
  global RECORDING_FLAG
  print(request.get_data())
  data = request.get_json()
  print("📥 Incoming Data:", data) 
  if not data:
    return jsonify({"Error":"No Data Received"}), 400
  if not RECORDING_FLAG:
    print('Not Recording')
    return jsonify({'status': 'not recording'}), 200 
  try:
    #get variables from json data
    timestamp = datetime.utcnow().isoformat()
    ax = data.get("ax")
    ay = data.get("ay")
    az = data.get("az")
    gx = data.get("gx")
    gy = data.get("gy")
    gz = data.get("gz") 

    with open(IMU_CSV, mode='a', newline='') as file: #append the new line
      writer = csv.writer(file)
      writer.writerow([timestamp, ax, ay, az, gx, gy, gz])
    return jsonify({'status':'success'}),200
  except Exception as E:
    jsonify({'Error': str(E)}), 500

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=PORT, debug=True)
