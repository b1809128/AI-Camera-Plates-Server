from flask import Flask, render_template, Response
import cv2

app = Flask(__name__)
video_capture = cv2.VideoCapture(0)


def generate_frames():
    while True:
        success, frame = video_capture.read()

        if not success:
            break

        ret, jpeg = cv2.imencode('.jpg', frame)
        frame = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('capture.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    success, frame = video_capture.read()
    if success:
        cv2.imwrite('captured_image.jpg', frame)
    return render_template('capture.html')

if __name__ == '__main__':
    app.run(debug=True)
