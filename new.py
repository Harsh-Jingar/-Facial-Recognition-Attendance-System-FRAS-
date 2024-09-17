import cv2
import face_recognition

def test_image_conversion(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print("Failed to load image")
        return

    print(f"Original image shape: {image.shape}")
    print(f"Original image dtype: {image.dtype}")

    # Convert image to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    print(f"Converted image shape: {rgb_image.shape}")
    print(f"Converted image dtype: {rgb_image.dtype}")

    try:
        face_encodings = face_recognition.face_encodings(rgb_image)
        if face_encodings:
            print("Face encoding successful")
        else:
            print("No faces found in image")
    except Exception as e:
        print(f"Error during face encoding: {e}")

test_image_conversion("D:\\Harsh\\my work\\PDS Project\\faces\\raj.jpeg")
