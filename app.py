from flask import Flask, render_template, Response, jsonify, request
from datetime import datetime
# from PIL import Image
from PIL import ImageGrab
import cv2
import torch
# import math
import function.utils_rotate as utils_rotate
from IPython.display import display
import os
# import time
# import argparse
import function.helper as helper
# import pandas as pd
# import csv
from flask_mysqldb import MySQL, MySQLdb
import MySQLdb.cursors
# db = pymysql.connect("localhost", "root", "", "camera_ai","3306")


app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'camera_ai'

mysql = MySQL(app)
app.app_context().push()
connt = mysql.connection
cursor = mysql.connection.cursor()
# with app.app_context():
#     cursor = mysql.connection.cursor()


now = datetime.now()
dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

plate_array = []
flag_stop_video = False

# load model
yolo_LP_detect = torch.hub.load(
    'yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load(
    'yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.60


def gen():
    # cap = cv2.VideoCapture(
    #     "D:/QuocHuy/Project/AI/Flask-Server-AI-Camera/demo.mp4")
    # cursor = mysql.connection.cursor()
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

                        checkToAddDatabase(lp)

                        (text_width, text_height) = cv2.getTextSize(
                            lp, cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, thickness=1)[0]
                        text_offset_x = int(plate[0])
                        text_offset_y = int(plate[1]-10)
                        # make the coords of the box with a small padding of two pixels
                        box_coords = ((text_offset_x, text_offset_y), (text_offset_x +
                                                                       text_width + 70, text_offset_y-50 - text_height - 2))

                        if returnValueStatusChecked(lp) == 1:
                            cv2.rectangle(
                                frame, box_coords[0], box_coords[1], (0, 0, 0), cv2.FILLED)
                            cv2.putText(frame, "Tinh trang: "+str(displayStatusPlate(lp)), (int(plate[0]), int(
                                plate[1]-55)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Su kien: XE VAO UBND", (int(plate[0]), int(
                                plate[1]-45)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Loai xe: O TO", (int(plate[0]), int(
                                plate[1]-35)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Bien so: "+lp, (int(plate[0]), int(
                                plate[1]-25)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Thoi diem: "+dt_string, (int(plate[0]), int(
                                plate[1]-15)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        else:
                            cv2.rectangle(
                                frame, box_coords[0], box_coords[1], (0, 0, 255), cv2.FILLED)
                            cv2.putText(frame, "Tinh trang: "+str(displayStatusPlate(lp)), (int(plate[0]), int(
                                plate[1]-55)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Su kien: XE VAO UBND", (int(plate[0]), int(
                                plate[1]-45)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Loai xe: O TO", (int(plate[0]), int(
                                plate[1]-35)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Bien so: "+lp, (int(plate[0]), int(
                                plate[1]-25)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                            cv2.putText(frame, "Thoi diem: "+dt_string, (int(plate[0]), int(
                                plate[1]-15)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        if not ret:
            print("Error: failed to capture image")
            break
        cv2.imwrite('demo.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + open('demo.jpg', 'rb').read() + b'\r\n')
        if flag_stop_video:
            break
# HAM KIEM TRA DE THEM DU LIEU


def checkToAddDatabase(lp):
    # KIEM TRA CAC BS DUOC PHEP VAO CO QUAN
    cursor.execute("SELECT * FROM detected where plate='"+lp+"'")
    checkDetected = cursor.fetchall()

    if (len(checkDetected) > 0):
        # NEU BS DUOC PHEP DA LUU THI THEM BS VAO DU LIEU TRONG NGAY
        insertCarDetected(checkDetected[0][1], lp)
    else:
        # KIEM TRA CAC BS DA VAO TRONG NGAY
        cursor.execute("SELECT * FROM detect_today where plate='"+lp+"'")
        checkDetectToday = cursor.fetchall()
        # print(len(checkDetected))
        if ((len(checkDetectToday) >= 1)):
            # NEU BS TRONG NGAY DA TON TAI THI THEM VAO "XE DA VAO" || "UNKNOW"
            # insertCarNotDetected(lp, 1)
            inserted = 1
        else:
            insertCarNotDetected(lp, 0)
        insertCarNotDetected(lp, 0)

# HAM KIEM TRA HIEN THI RA VIDEO


def displayStatusPlate(lp):
    # KIEM TRA CAC BS DUOC PHEP VAO CO QUAN TRA VE TINH TRANG THONG TIN BS
    cursor.execute("SELECT * FROM detected where plate='"+lp+"'")
    checkDetected = cursor.fetchall()
    if (len(checkDetected) > 0):
        return checkDetected[0][1]
    else:
        cursor.execute(
            "SELECT * FROM detect_today where plate='"+lp+"'")
        checkDetectToday = cursor.fetchall()
        if (len(checkDetectToday) > 0 and checkDetectToday[0][1] == "XE DA VAO"):
            # if ():
            return "XE DA VAO"

        return "KHONG CO DU LIEU"


def returnValueStatusChecked(lp):
    # KIEM TRA CAC BS DUOC PHEP VAO CO QUAN TRA VE TINH TRANG THONG TIN BS
    cursor.execute("SELECT * FROM detected where plate='"+lp+"'")
    checkDetected = cursor.fetchall()
    if (len(checkDetected) > 0):
        return 1
    else:
        return 0


def insertCarNotDetected(lp, flag):
    if (flag == 0):
        cursor.execute("SELECT * FROM detect_today where plate='"+lp+"'")
        check_plate_empty = cursor.fetchall()
        if (len(check_plate_empty) == 0):
            cursor.execute(
                "INSERT INTO `detect_today` (`id`, `status`, `event`, `type`, `plate`, `date`) VALUES (NULL, 'KHONG CO DU LIEU', 'XE VAO UBND', 'O TO', '"+lp+"', current_timestamp())")
            connt.commit()
    if (flag == 1):
        insertFlag = 0
        cursor.execute(
            "INSERT INTO `detect_today` (`id`, `status`, `event`, `type`, `plate`, `date`) VALUES (NULL, 'XE DA VAO', 'XE VAO UBND', 'O TO', '"+lp+"', current_timestamp())")
        connt.commit()
        insertFlag = 1
        if (insertFlag == 1):
            cursor.execute(
                "UPDATE `detect_today` SET `status` = 'XE DA VAO' WHERE `detect_today`.`plate` = '"+lp+"';")
            connt.commit()
    # print({"Inserted data: ": lp, "Flag: ": flag})


def insertCarDetected(status, lp):
    cursor.execute(
        "INSERT INTO `detect_today` (`id`, `status`, `event`, `type`, `plate`, `date`) VALUES (NULL, '"+status+"', 'XE VAO UBND', 'O TO', '"+lp+"', current_timestamp())")
    connt.commit()
    # print("Inserted data" + lp)


@app.route('/')
def index():
    return render_template('index.html', dt_string=dt_string)


@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/capture', methods=['POST'])
# def capture():
#     cap = cv2.VideoCapture("D:/QuocHuy/Project/AI/Flask-Server-AI-Camera/demo.mp4")
#     success, frame = cap.read()
#     if success:
#         cv2.imwrite('captured_image.jpg', frame)
#     return render_template('index.html')


@app.route('/capture')
def capture_screen():
    # Chụp màn hình và lưu vào tệp captured_screen.png
    screenshot = ImageGrab.grab()
    screenshot_path = os.path.join(os.getcwd(), 'captured_screen.jpg')
    screenshot.save(screenshot_path)
    # print('Screenshot captured: {screenshot_path}')
    return render_template('index.html')


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
    # print(returnObjectCheck('65A26616'))
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM detect_today ORDER BY id DESC limit 2 ")
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

# Requirements.txt
# pipreqs --encoding=utf8 D:\QuocHuy\Project\AI\Flask-Server-AI-Camera
#run localhost - python app.py