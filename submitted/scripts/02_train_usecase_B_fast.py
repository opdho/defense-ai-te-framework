"""
Usecase Model B — fast robust model for framework demo.
Purpose:
  - Good clean performance
  - Better retention under adverse scenario-based evaluation

Recommended use:
  python 02_train_usecase_B_fast.py \
      --data augmented_model_B/data_model_B.yaml \
      --device 0
"""

import argparse
import shutil
from pathlib import Path
from ultralytics import YOLO


def save_best_weights(project: str, name: str, out_name: str) -> Path | None:
    best = Path(project) / name / "weights" / "best.pt"
    if not best.exists():
        print(f"[WARN] best.pt not found: {best}")
        return None
    dst = Path(out_name)
    shutil.copy2(best, dst)
    print(f"[OK] copied best weights -> {dst.resolve()}")
    return dst


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="augmented_model_B/data_model_B.yaml", help="YOLO dataset yaml including adverse/augmented train set")
    parser.add_argument("--model", default="yolo11s.pt", help="Recommended: yolo11s.pt for better robustness with manageable cost")
    parser.add_argument("--epochs", type=int, default=70, help="Still relatively short, but enough to separate A/B usecase")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16, help="Use 8 if GPU RAM is limited")
    parser.add_argument("--device", default="0")
    parser.add_argument("--project", default="runs/usecase_models")
    parser.add_argument("--name", default="model_B_fast")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-best-as", default="model_B_usecase.pt")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"augmented dataset yaml not found: {data_path}\n"
            "Run your adverse dataset builder first, then retry."
        )

    print("=" * 72)
    print("[USECASE MODEL B] fast robust candidate")
    print(f"  data   : {data_path}")
    print(f"  model  : {args.model}")
    print(f"  epochs : {args.epochs}")
    print(f"  device : {args.device}")
    print("  intent : good clean performance + stronger adverse robustness")
    print("=" * 72)

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        workers=args.workers,
        patience=args.patience,
        seed=args.seed,
        pretrained=True,
        verbose=True,
        amp=True,
        cache=False,
        # stronger but still practical augmentation for robust usecase model
        hsv_h=0.015,
        hsv_s=0.70,
        hsv_v=0.45,
        degrees=10.0,
        translate=0.10,
        scale=0.35,
        shear=2.0,
        perspective=0.0001,
        flipud=0.03,
        fliplr=0.5,
        mosaic=0.80,
        mixup=0.10,
        copy_paste=0.20,
        close_mosaic=10,
        lr0=0.008,
        lrf=0.01,
        cos_lr=True,
    )

    save_best_weights(args.project, args.name, args.save_best_as)
    print("[NEXT] Register this checkpoint as candidate B in your model registry.")


if __name__ == "__main__":
    main()
