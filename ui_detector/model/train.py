from ultralytics import YOLO
import torch

def main():

    device = "cuda" if  torch.cuda.is_available() else "cpu"

    print(f"Training device: {device}")

    config = "ui_detector/train_data_v3/data.yaml"

    model_size = "yolov8l.pt"

    epochs = 500
    image_size = 640
    model_folder_name = "ui_detector_model_v0.3"

    model = YOLO(model_size)

    print("Train Starting...")
    result = model.train(
        data=config,
        epochs=epochs,
        imgsz=image_size,
        device=device,
        name=model_folder_name
    )
    print("Train complete")
    print(f"Model save deructory: {result.save_dir}")

if __name__ == "__main__":
    main()