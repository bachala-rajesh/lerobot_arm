import cv2
from deepface import DeepFace

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Analyze the frame (face recognition + emotion, etc.)
    result = DeepFace.analyze(
        frame,
        actions=['age', 'gender', 'race', 'emotion'],
        enforce_detection=False  # Set to True for stricter face detection
    )

    # Draw results on frame
    if isinstance(result, list):
        # Multiple faces
        for face in result:
            x, y, w, h = face['region']['x'], face['region']['y'], face['region']['w'], face['region']['h']
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
            label = f"{face['dominant_emotion']}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
    else:
        # Single face
        x, y, w, h = result['region']['x'], result['region']['y'], result['region']['w'], result['region']['h']
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
        label = f"{result['dominant_emotion']}, {result['age']}, {result['gender']}"
        cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

    cv2.imshow("DeepFace Real-Time Demo", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
