from ultralytics import YOLO
import torch

def main():

    device = "cuda" if  torch.cuda.is_available() else "cpu"

    print(f"Training device: {device}")

    config = "ui_detector/model/train_data_v0.4/yolo_dataset/data.yaml"

    model_size = "ui_detector/model/last.pt"

    epochs = 500
    image_size = 640
    model_folder_name = "ui_detector_model_v0.4"

    model = YOLO(model_size)

    print("Train Starting...")

    result = model.train(
        data=config,
        epochs=epochs,
        imgsz=image_size,
        device=device,
        name=model_folder_name,
        patience=50, 
        batch=8
    )

    print("Train complete")
    print(f"Model save derictory: {result.save_dir}")


if __name__ == "__main__":
    main()