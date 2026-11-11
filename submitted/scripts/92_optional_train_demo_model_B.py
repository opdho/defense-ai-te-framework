import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description='Optional helper: train a quick robust/use-case demo model.')
    parser.add_argument('--data', required=True)
    parser.add_argument('--model', default='yolo11n.pt')
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--device', default='0')
    parser.add_argument('--project', default='runs/framework_demo_models')
    parser.add_argument('--name', default='demo_model_B')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--patience', type=int, default=15)
    args = parser.parse_args()

    model = YOLO(args.model)
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        workers=args.workers,
        patience=args.patience,
        pretrained=True,
        verbose=True,
        hsv_h=0.020,
        hsv_s=0.70,
        hsv_v=0.45,
        degrees=12.0,
        translate=0.12,
        scale=0.45,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.25,
        amp=True,
        val=True,
        plots=True,
    )
    best = Path(results.save_dir) / 'weights' / 'best.pt'
    if best.exists():
        shutil.copy2(best, 'demo_model_B.pt')
    print('\n[OK] quick demo model B written -> demo_model_B.pt')


if __name__ == '__main__':
    main()
