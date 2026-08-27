import dlib
import cv2
import numpy as np
import time

# Initialize dlib's face detector and facial landmarks predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")  # Download this file from dlib website

# Read image
def detect_face(filename):
    img = cv2.imread(filename)  
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect faces
    start_time = time.time()
    faces = detector(gray)
    end_time = time.time()
    print("detector elapsed Time:", end_time - start_time)
    print(faces)
    for face in faces:
        x1 = face.left()
        y1 = face.top()
        x2 = face.right()
        y2 = face.bottom()

        margin = 30
        startY = y1 - margin if y1 - margin > 0 else 0
        startX = x1 - margin if x1 - margin > 0 else 0
        endY = y2 + margin if y2 + margin < img.shape[0] else img.shape[0]
        endX = x2 + margin if x2 + margin < img.shape[1] else img.shape[1]
        crop_img = img[startY:endY, startX:endX]
        cv2.imshow("cropped", crop_img)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)

        # Get facial landmarks
        start_time = time.time()
        landmarks = predictor(gray, face)
        end_time = time.time()
        print("predictor elapsed Time:", end_time - start_time)

        # Get specific landmarks for eyes
        left_eye = (landmarks.part(36).x, landmarks.part(36).y)
        right_eye = (landmarks.part(45).x, landmarks.part(45).y)
    
        # Draw points on image
        cv2.circle(img, left_eye, 3, (0, 255, 0), -1)
        cv2.circle(img, right_eye, 3, (0, 255, 0), -1)

    # Show image
    cv2.imshow(filename, img)

if __name__ == "__main__":
    detect_face('0.png')   
    detect_face('90.png')
    detect_face('180.png')
    detect_face('270.png')

    cv2.waitKey(0)
