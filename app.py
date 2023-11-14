from flask import Flask, render_template, Response
from datetime import datetime
from PIL import Image
import cv2
import torch
import math
import function.utils_rotate as utils_rotate
from IPython.display import display
import os
import time
import argparse
import function.helper as helper
import pandas as pd
import csv

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


now = datetime.now()
dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
# dateStr = today.strftime("%d/%m/%Y")

# load model
yolo_LP_detect = torch.hub.load(
    'yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load(
    'yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.60

prev_frame_time = 0
new_frame_time = 0


def check_plate(plate):
    ub_list_plate = ["65A19777", "65A29999"]
    for i in ub_list_plate:
        if (i == plate):
            return 1
        else:
            return 0


def gen():
    cap = cv2.VideoCapture("D:/QuocHuy/Project/AI/Flask-Server-AI-Camera/test_image/test.mp4")

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
                    # if (check_plate(list_read_plates) == 1):
                    #     cv2.putText(frame, "Status: Xe co quan UBND", (int(plate[0]), int(
                    #         plate[1]-30)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                    # else:
                    #     cv2.putText(frame, "Status: Unknow Data", (int(plate[0]), int(
                    #         plate[1]-30)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Kiem tra: Khong co du lieu", (int(plate[0]), int(
                            plate[1]-30)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Thoi diem: "+dt_string, (int(plate[0]), int(
                            plate[1]-20)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                        cv2.putText(frame, "Bien so: "+lp, (int(plate[0]), int(
                            plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        if not ret:
            print("Error: failed to capture image")
            break

        cv2.imwrite('demo.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + open('demo.jpg', 'rb').read() + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
