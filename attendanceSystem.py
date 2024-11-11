import cv2
import os
import face_recognition
import datetime
from connection import conn
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Load today's date for table creation and attendance tracking
today = datetime.date.today().strftime("%d_%m_%Y")

known_faces = []
known_names = []

# Load known faces and encodings from the 'static/faces' folder
def get_known_encodings():
    global known_faces, known_names
    print("Loading known faces...")
    known_faces = []
    known_names = []

    for filename in os.listdir('static/faces'):
        file_path = os.path.join('static/faces', filename)
        try:
            images = face_recognition.load_image_file(file_path)
            encodings = face_recognition.face_encodings(images)
            if encodings:  # Check if any encoding is found
                known_faces.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])
            else:
                print(f"No faces found in {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

# Get the total number of registered users
def totalreg():
    return len(os.listdir('static/faces/'))

# Extract attendance from the database
def extract_attendance():
    try:
        results = conn.read(f"SELECT * FROM {today}")
        return results
    except Exception as e:
        print(f"Error reading attendance data: {e}")
        return []

# Mark attendance for a recognized person
def mark_attendance(person):
    name = person.split('_')[0]
    roll_no = int(person.split('_')[1])
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    try:
        exists = conn.read(f"SELECT * FROM {today} WHERE roll_no = {roll_no}")
        if len(exists) == 0:
            conn.insert(f"INSERT INTO {today} (name, roll_no, time) VALUES (%s, %s, %s)", 
                        (name, roll_no, current_time))
            print(f"Attendance marked for {name} ({roll_no}) at {current_time}")
            return f"Attendance marked for {name} ({roll_no}) at {current_time}", "success"
        else:
            print(f"Attendance already marked for {name} ({roll_no})")
            return f"Attendance already marked for {name} ({roll_no})", "info"
    except Exception as e:
        print(f"Error marking attendance: {e}")
        return "Error marking attendance", "error"

# Identify and mark attendance using the webcam with 'Q' to capture
def identify_person():
    print("Known faces loaded successfully.")
    video_capture = cv2.VideoCapture(0)
    print("Opening camera...")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to capture frame from camera.")
            break

        # Flip the frame for a mirror-like effect
        flipped_frame = cv2.flip(frame, 1)

        # Display instruction text on the camera feed
        text = "Press Q to Mark Attendance"
        font = cv2.FONT_HERSHEY_COMPLEX
        font_scale = 0.9
        font_color = (0, 0, 200)
        thickness = 2

        # Calculate the text position
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (flipped_frame.shape[1] - text_size[0]) // 2
        text_y = 50

        # Display the text on the frame
        cv2.putText(flipped_frame, text, (text_x, text_y), font, font_scale, font_color, thickness, cv2.LINE_AA)
        cv2.imshow('Camera', flipped_frame)

        # Wait for user to press 'Q' to start face recognition
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Starting face recognition...")
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

            if recognized_names:
                feedback, message_type = mark_attendance(name)
                print(feedback)
                return feedback, message_type
            else:
                return "No known faces recognized!", "error"
            break

    video_capture.release()
    cv2.destroyAllWindows()
    print("Camera closed.")

# Home route
@app.route('/')
def home():
    try:
        conn.create(f"CREATE TABLE IF NOT EXISTS {today} (name VARCHAR(30), roll_no INT, time VARCHAR(10))")
    except Exception as e:
        print(f"Error creating table: {e}")

    userDetails = extract_attendance()
    get_known_encodings()

    message = request.args.get('message', '')
    message_type = request.args.get('message_type', 'success')
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"),
                           totalreg=totalreg(), userDetails=userDetails,
                           message=message, message_type=message_type)

# Video feed route for recognizing persons
@app.route('/video_feed', methods=['GET'])
def video_feed():
    feedback, message_type = identify_person()
    return redirect(url_for('home', message=feedback, message_type=message_type))

# Add a new user with captured image
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['newusername']
        roll_no = request.form['newrollno']
        userimagefolder = 'static/faces'

        if not os.path.isdir(userimagefolder):
            os.makedirs(userimagefolder)

        video_capture = cv2.VideoCapture(0)
        print("Camera opened for user registration...")

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Failed to capture frame.")
                break

            flipped_frame = cv2.flip(frame, 1)

            text = "Press Q to Capture & Save the Image"
            font = cv2.FONT_HERSHEY_COMPLEX
            font_scale = 0.9
            font_color = (0, 0, 200)
            thickness = 2

            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = 50

            cv2.putText(flipped_frame, text, (text_x, text_y), font, font_scale, font_color, thickness, cv2.LINE_AA)
            cv2.imshow('Camera', flipped_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                img_name = f"{name}_{roll_no}.jpg"
                cv2.imwrite(os.path.join(userimagefolder, img_name), frame)
                print(f"Image saved as {img_name}")
                break

        video_capture.release()
        cv2.destroyAllWindows()

        feedback = f"User {name} added successfully!"
        message_type = "success"

        userDetails = extract_attendance()
        get_known_encodings()
        return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"),
                               totalreg=totalreg(), userDetails=userDetails, 
                               message=feedback, message_type=message_type)

    return render_template('add_user.html')

# Handle favicon request to avoid 404 error
@app.route('/favicon.ico')
def favicon():
    return '', 204

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
