from retinaface import RetinaFace
import cv2

def rotate(img, left_eye, right_eye, nose):

    nose_x, nose_y = nose
    left_eye_x, left_eye_y = left_eye
    right_eye_x, right_eye_y = right_eye

    if (nose_y > left_eye_y) and (nose_y > right_eye_y):
        return img # no need to rotate
    elif (nose_y < left_eye_y) and (nose_y < right_eye_y):
        return cv2.flip(img, flipCode=-1) # 180 degrees
    elif (nose_x < left_eye_x) and (nose_x < right_eye_x):
        transposed = cv2.transpose(img)
        return cv2.flip(transposed, flipCode=0) # 90 degrees 
    else:
        transposed = cv2.transpose(img)
        return cv2.flip(transposed, flipCode=1) # 270 degrees 

def detect(img):
    obj = RetinaFace.detect_faces(img_path=img)

    if type(obj) == dict:
        for key in obj:
            identity = obj[key]

            facial_area = identity["facial_area"]
            facial_img = img[facial_area[1]: facial_area[3],
                             facial_area[0]: facial_area[2]]

            landmarks = identity["landmarks"]
            left_eye = landmarks["left_eye"]
            right_eye = landmarks["right_eye"]
            nose = landmarks["nose"]
            mouth_right = landmarks["mouth_right"]
            mouth_left = landmarks["mouth_left"]

            cv2.rectangle(img, (facial_area[0], facial_area[1]),
                          (facial_area[2], facial_area[3]), (0, 255, 0), 2)
            cv2.circle(img, (int(left_eye[0]), int(
                left_eye[1])), 2, (255, 0, 0), 2)
            cv2.circle(img, (int(right_eye[0]), int(
                right_eye[1])), 2, (0, 0, 255), 2)
            cv2.circle(img, (int(nose[0]), int(nose[1])), 2, (0, 255, 0), 2)
            cv2.circle(img, (int(mouth_left[0]), int(
                mouth_left[1])), 2, (0, 155, 255), 2)
            cv2.circle(img, (int(mouth_right[0]), int(
                mouth_right[1])), 2, (0, 155, 255), 2)

            img = rotate(img, right_eye, left_eye, nose)
            return img
    
    return img

def detect_face(filename):
    img = cv2.imread(filename)
    img = detect(img)
    cv2.imshow(filename, img)

if __name__ == "__main__":
    detect_face('0.png')
    detect_face('90.png')
    detect_face('180.png')
    detect_face('270.png')

    cv2.waitKey(0)
