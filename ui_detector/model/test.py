from ultralytics import YOLO
from PIL import Image
import cv2
import os

def main():

    model_path = 'runs/detect/ui_detector_model_v0.12/weights/best.pt'
    model = YOLO(model_path)

    image_to_predict = 'ui_detector/model/image.png'

    results = model.predict(image_to_predict, conf=0.5)

    result = results[0]

    print(f"Найдено {len(result.boxes)} объектов на изображении.")
    
    for box in result.boxes:
        x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]
        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]
        confidence = round(box.conf[0].item(), 2)

        print(f" - Класс: {class_name}, Уверенность: {confidence}")
        print(f"   Координаты: (x1: {x1}, y1: {y1}) - (x2: {x2}, y2: {y2})")

    annotated_image = result.plot()
    
    annotated_image_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
    
    output_filename = "result.png"
    
    cv2.imwrite(output_filename, annotated_image_bgr)
    
    print(f"\n✅ Результат успешно сохранен в файл: {os.path.abspath(output_filename)}")


if __name__ == '__main__':
    main()