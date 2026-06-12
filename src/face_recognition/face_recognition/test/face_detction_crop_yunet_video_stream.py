
"""
    Face Alignment Pipeline: Step-by-Step
    1. Capture Frame
    Read a frame from the camera using OpenCV.

    2. Detect Face and Landmarks
    Use a face detector (like Yunet) to detect face bounding box and eye landmarks.

    3. Expand Bounding Box
    Enlarge the detected bounding box by a margin (e.g., 30%) to ensure the whole face is captured after rotation.

    4. Crop Region of Interest (ROI)
    Crop the image using the expanded bounding box.

    5. Adjust Eye Coordinates
    Subtract the top-left (x, y) of the expanded bounding box from each eye landmark to get ROI-relative coordinates.

    6. Compute Eye Angle
    Calculate the angle between the two eyes using atan2.

    7. Smooth the Angle
    Apply exponential smoothing to the angle to reduce jitter.

    8. Align the Face
    Rotate the ROI around the eye center using the smoothed angle.

    9. Display Results
    Show the original frame with bounding box and landmarks.
    Show the aligned face in a separate window.

"""

import cv2
import numpy as np
import math


def compute_angle(left_eye, right_eye):
    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    
    angle = math.degrees(math.atan2(dy, dx))
    # convert radians into degrees
    # angle = np.rad2deg(angle)
    print(angle)
    return angle
    
def align_face(roi_frame, left_eye, right_eye):
    global smooth_angle
    height, width = roi_frame.shape[:2]
    eye_center = ((left_eye[0] + right_eye[0])//2, (left_eye[1] + right_eye[1])//2)
    angle = compute_angle(left_eye, right_eye)
    
    smooth_angle = smooth_value(smooth_angle, angle)
    
    # get Rotation matrix
    M = cv2.getRotationMatrix2D(eye_center, smooth_angle, 1.0)
    
    # apply affine transformation
    aligned_face = cv2.warpAffine(roi_frame, M, (width, height), flags=cv2.INTER_CUBIC)
    return aligned_face

def smooth_value(prev, new, alpha = 0.3):
    if prev is  None:
        return new
    return prev * (1-alpha) + alpha * new

def expand_bbox(x, y, w, h, img_width, img_height, margin=0.3):
    # margin: 0.3 means 30% extra on each side
    dw = int(w * margin)
    dh = int(h * margin)
    nx = max(x - dw, 0)
    ny = max(y - dh, 0)
    nw = min(w + 2 * dw, img_width - nx)
    nh = min(h + 2 * dh, img_height - ny)
    return nx, ny, nw, nh

cap = cv2.VideoCapture(0)
smooth_angle= None
alpha = 0.3

face_detector = cv2.FaceDetectorYN.create("face_detection_yunet_2023mar_int8bq.onnx", "", (320, 320), score_threshold=0.7)
i = 0
aligned_face = None
while True:
    ret, frame = cap.read()
 
    if ret:
        height, width = frame.shape[:2]
        face_detector.setInputSize((width, height))
        _, faces = face_detector.detect(frame)
        
        if faces is not None:
            i += 1
            print(f"face detected: {i} times")
            for face in faces:
                x, y, w, h = map(int, face[:4])
                left_eye = tuple(map(int, face[4:6]))
                right_eye = tuple(map(int, face[6:8]))
                
                # region of interest
                # roi_frame = frame[y:y+h+1, x:x+w+1]
                nx, ny, nw, nh = expand_bbox(x, y, w, h, width, height, margin=0.3)
                roi_frame = frame[ny:ny+nh, nx:nx+nw]
                
                # Adjust eyes to ROI coordinates
                # roi_left_eye = (left_eye[0] - x, left_eye[1] - y)
                # roi_right_eye = (right_eye[0] - x, right_eye[1] - y)
                roi_left_eye = (left_eye[0] - nx, left_eye[1] - ny)
                roi_right_eye = (right_eye[0] - nx, right_eye[1] - ny)
                
                # align face
                aligned_face = align_face(roi_frame, roi_left_eye, roi_right_eye)
                
                # draw markers
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (left_eye[0], left_eye[1]), 5, (255, 0, 0), -1)
                cv2.circle(frame, (right_eye[0], right_eye[1]), 5, (255, 0, 0), -1)
                cv2.imshow("aligned_face", aligned_face)
                
            
    else:
        print("Failed to capture the frame...")

    # display the image
    cv2.imshow("frame", frame)
    key = cv2.waitKey(50)
    if key is ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
    
    
