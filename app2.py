from flask import Flask, render_template, Response, jsonify, request
from datetime import datetime
# from PIL import Image
import cv2
import torch
# import math
import function.utils_rotate as utils_rotate
from IPython.display import display
# import os
# import time
# import argparse
import function.helper as helper
# import pandas as pd
# import csv
from flask_mysqldb import MySQL, MySQLdb
# db = pymysql.connect("localhost", "root", "", "camera_ai","3306")


app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'camera_ai'

mysql = MySQL(app)
app.app_context().push()
cursor = mysql.connection.cursor()
# with app.app_context():
#     cursor = mysql.connection.cursor()


now = datetime.now()
dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

plate_array = []

# load model
yolo_LP_detect = torch.hub.load(
    'yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load(
    'yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.60


def check_plate(plate):
    ub_list_plate = ["65A19777", "65A29999"]
    for i in ub_list_plate:
        if (i == plate):
            return 1
        else:
            return 0


def gen():
    # cap = cv2.VideoCapture("D:/QuocHuy/Project/AI/Flask-Server-AI-Camera/test_image/test.mp4")
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()

        plates = yolo_LP_detect(frame, size=640)
        list_plates = plates.pandas().xyxy[0].values.tolist()
        list_read_plates = set()

        for plate in list_plates:
            flag = 0
            x = int(plate[0])  # xmin
            y = int(plate[1])  # ymin
            w = int(plate[2] - plate[0])  # xmax - xmin
            h = int(plate[3] - plate[1])  # ymax - ymin
            crop_img = frame[y:y+h, x:x+w]
            cv2.rectangle(frame, (int(plate[0]), int(plate[1])), (int(
                plate[2]), int(plate[3])), color=(0, 0, 225), thickness=2)
            cv2.imwrite("crop.jpg", crop_img)
            rc_image = cv2.imread("crop.jpg")
            lp = ""
            for cc in range(0, 2):
                for ct in range(0, 2):
                    lp = helper.read_plate(
                        yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                    if lp != "unknown":
                        list_read_plates.add(lp)
                        cursor.execute(
                            "SELECT * FROM detect_today where plate='"+lp+"'")
                        checkDetectToday = cursor.fetchall()
                        if (len(checkDetectToday) > 0):
                            count = 1
                        else:
                            cursor.execute(
                                "INSERT INTO detect_today VALUES('','Khong co du lieu','Xe vao co quan','O to','65A-31348','')")
                            mysql.connection.commit()

                        (text_width, text_height) = cv2.getTextSize(
                            lp, cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, thickness=1)[0]
                        text_offset_x = int(plate[0])
                        text_offset_y = int(plate[1]-10)
                        # make the coords of the box with a small padding of two pixels
                        box_coords = ((text_offset_x, text_offset_y), (text_offset_x +
                                                                       text_width + 60, text_offset_y-40 - text_height - 2))
                        cv2.rectangle(
                            frame, box_coords[0], box_coords[1], (0, 0, 0), cv2.FILLED)
                        cv2.putText(frame, "Loai xe: O to", (int(plate[0]), int(
                            plate[1]-40)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Kiem tra: Khong co du lieu", (int(plate[0]), int(
                            plate[1]-30)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Thoi diem: "+dt_string, (int(plate[0]), int(
                            plate[1]-20)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Bien so: "+lp, (int(plate[0]), int(
                            plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        if not ret:
            print("Error: failed to capture image")
            break
        global plate_array
        plate_array += list_read_plates
        cv2.imwrite('demo.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + open('demo.jpg', 'rb').read() + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html', dt_string=dt_string)


@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/returnjson', methods=['GET'])
def ReturnJSON():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM accs_hist")
    rv = cursor.fetchall()
    # print(len((rv)))
    # return jsonify(rv)
    arrayInfo = []
    arrayObjects = {}
    for result in rv:
        # arrayObjects = {"id": result["id"], "": result[""], "": result[""],
        #                 "": result[""], "": result[""], "": result[""]}
        arrayObjects = {
            "id": int(result["accs_id"]), "plate": result["accs_date"]}
        arrayInfo.append(arrayObjects)
        arrayObjects = {}

    return jsonify(arrayInfo)


@app.route('/countRowData', methods=['GET'])
def countRowData():
    # count = 0
    if (request.method == 'GET'):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM detect_today where date=curdate()")
        checkDetectToday = cursor.fetchall()
        return jsonify({"count": len(checkDetectToday)})


@app.route('/loadData', methods=['GET', 'POST'])
def loadData():
    # data = [{
    #     "id": 1,
    #     "plate": "65A19777",
    #     "created_at": "08:35:20 18/11/2023"
    # }, {
    #     "id": 2,
    #     "plate": "65A25896",
    #     "created_at": "08:38:20 18/11/2023"
    # }, {
    #     "id": 3,
    #     "plate": "65A19777",
    #     "created_at": "08:38:20 18/11/2023"
    # }]

    # newData = []
    # for i in data:
    #     if (i["plate"] == "65A19777"):
    #         # print(i)
    #         return jsonify(response=i)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM detect_today ORDER BY id DESC limit 3 ")
    checkDetectToday = cursor.fetchall()
    arrayInfo = []
    arrayObjects = {}
    for result in checkDetectToday:
        arrayObjects = {"id": result["id"], "status": result["status"], "event": result["event"],
                        "type": result["type"], "plate": result["plate"], "date": result["date"]}
        arrayInfo.append(arrayObjects)
        arrayObjects = {}

    return jsonify([arrayInfo])


if __name__ == '__main__':
    app.run(debug=True)
    # print(plate_array)
    # socketio.run(app)

# Requirements.txt
# pipreqs --encoding=utf8 D:\QuocHuy\Project\AI\Flask-Server-AI-Camera
