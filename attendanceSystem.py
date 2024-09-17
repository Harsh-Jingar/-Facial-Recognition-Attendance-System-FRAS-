import cv2
import os
import face_recognition
import datetime
from connection import conn
from flask import Flask, render_template, request

app = Flask(__name__)

# Load known faces and their names from the 'faces' folder
print("Loading known faces...")
known_faces = []
known_names = []

today = datetime.date.today().strftime("%d_%m_%Y")

def get_known_encodings():
    global known_faces, known_names
    print("Loading known faces...")
    known_faces = []
    known_names = []

    for filename in os.listdir('static/faces'):
        images = face_recognition.load_image_file(os.path.join('static/faces', filename))
        encoding = face_recognition.face_encodings(images)[0]
        known_faces.append(encoding)
        known_names.append(os.path.splitext(filename)[0])

def totalreg():
    return len(os.listdir('static/faces/'))

def extract_attendance():
    results = conn.read(f"SELECT * FROM {today}")
    return results

def mark_attendance(person):
    name = person.split('_')[0]
    roll_no = int(person.split('_')[1])
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    exists = conn.read(f"SELECT * FROM {today} WHERE roll_no = {roll_no}")
    if len(exists) == 0:
        try:
            conn.insert(f"INSERT INTO {today} VALUES (%s, %s, %s)", (name, roll_no, current_time))
        except Exception as e:
            print(e)

def identify_person():
    print("Known faces loaded successfully.")
    video_capture = cv2.VideoCapture(0)
    print("Opening camera...")
    attendance_marked = False
    
    while True:
        ret, frame = video_capture.read()
        rgb_frame = frame[:, :, ::-1]
        
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        recognized_names = []
        
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_faces, face_encoding)
            name = 'Unknown'
            
            if True in matches:
                matched_indices = [i for i, match in enumerate(matches) if match]
                for index in matched_indices:
                    name = known_names[index]
                    recognized_names.append(name)

        if len(recognized_names) > 0:
            
            for name in recognized_names:
                mark_attendance(name) 
                        
            attendance_marked = True
              
        cv2.imshow('Camera', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q') or attendance_marked:
            break
    
    video_capture.release()
    cv2.destroyAllWindows()
    print("Camera closed.")

@app.route('/')
def home():
    conn.create(f"CREATE TABLE IF NOT EXISTS {today} (name VARCHAR(30), roll_no INT, time VARCHAR(10))")
    userDetails = extract_attendance()
    get_known_encodings()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(), userDetails=userDetails)

@app.route('/video_feed', methods=['GET'])
def video_feed():
    identify_person()
    userDetails = extract_attendance()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(), userDetails=userDetails)

@app.route('/add_user',  methods=['GET', 'POST'])
def add_user():
    name = request.form['newusername']
    roll_no = request.form['newrollno']
    userimagefolder = 'static/faces'
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    video_capture = cv2.VideoCapture(0)
    
    while True:
        ret, frame = video_capture.read()
        rgb_frame = frame[:, :, ::-1]
        flipped_frame = cv2.flip(frame, 1)
        
        text = "Press Q to Capture & Save the Image"
        font = cv2.FONT_HERSHEY_COMPLEX
        font_scale = 0.9
        font_color = (0, 0, 200)
        thickness = 2
        
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] - 450)
        
        cv2.putText(flipped_frame, text, (text_x, text_y), font, font_scale, font_color, thickness, cv2.LINE_AA)
        
        cv2.imshow('Camera', flipped_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            img_name = name+'_'+str(roll_no)+'.jpg'
            cv2.imwrite(userimagefolder+'/'+img_name, flipped_frame)
            break
        
    video_capture.release()
    cv2.destroyAllWindows()
    
    userDetails = extract_attendance()
    get_known_encodings()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(), userDetails=userDetails)

if __name__ == '__main__':
    app.run(debug=True)
