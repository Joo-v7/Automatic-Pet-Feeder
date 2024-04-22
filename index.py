from flask import Flask, request, render_template, jsonify
import datetime
import threading
import time
from RPLCD.i2c import CharLCD
import board
import busio
import RPi.GPIO as GPIO

app = Flask(__name__)

# LCD 설정
lcd_columns = 16
lcd_rows = 2
i2c = busio.I2C(board.SCL, board.SDA)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=lcd_columns, rows=lcd_rows)

SERVO_PIN = 18
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

feeding_times = []
servo_motor_running = False

def run_servo_motor():
    global servo_motor_running, feeding_times

    while servo_motor_running:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        if current_time.endswith(":00"):
            if current_time[:-3] in feeding_times:
                servo.ChangeDutyCycle(12.5)
                time.sleep(1)
                servo.ChangeDutyCycle(2.5)
                time.sleep(1)

        time.sleep(1)  # 1초마다 확인

    print("Servo motor stopped.")
    servo.stop()
    GPIO.cleanup()

def display_lcd():
    global feeding_times

    while True:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lcd.clear()
        lcd.write_string(current_time)
        lcd.cursor_pos = (1, 0) # 커서 위치를 LCD의 두 번째 줄로 이동
        if feeding_times: # 설정된 feeding_times가 있다면 이 코드 실행
            for time_val in feeding_times:
                lcd.write_string(time_val)
                time.sleep(1)  # 각 feeding time을 1초간 표시
                lcd.clear()
                lcd.write_string(current_time)  # 시간 다시 표시
                lcd.cursor_pos = (1, 0)
        else:
            lcd.write_string("No feeding times")
            time.sleep(5)  # 5초 동안 메시지 표시
            lcd.clear()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    count = int(request.form['count'])
    return render_template('submit.html', count=count)

@app.route('/result', methods=['POST'])
def result():
    global feeding_times, servo_motor_running

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = int(request.form['count'])

    new_feeding_times = []
    for i in range(1, count + 1):
        time_val = request.form.get(f'time{i}', '')
        new_feeding_times.append(time_val)

    if not servo_motor_running: # 서보모터가 실행중이지 않을때, False일때
        feeding_times = new_feeding_times
        servo_motor_running = True
        servo_thread = threading.Thread(target=run_servo_motor)
        lcd_thread = threading.Thread(target=display_lcd)
        servo_thread.start()
        lcd_thread.start()

    return render_template('result.html', current_time=current_time, feeding_times=feeding_times)

@app.route('/get_current_time')
def get_current_time():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(current_time=current_time)

@app.route('/get_feeding_times')
def get_feeding_times():
    global feeding_times
    return jsonify(feeding_times=feeding_times)

if __name__ == '__main__':
    app.run(debug=True)
