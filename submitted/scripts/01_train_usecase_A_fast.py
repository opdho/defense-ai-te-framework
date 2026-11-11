"""
Usecase Model A — fast baseline model for framework demo.
Purpose:
  - Good clean performance
  - Noticeable degradation under scenario-based adverse conditions

Recommended use:
  python 01_train_usecase_A_fast.py \
      --data <DATASET>/data.yaml \
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
    parser.add_argument("--data", default="data.yaml", help="YOLO dataset yaml for clean/original training set")
    parser.add_argument("--model", default="yolo11n.pt", help="Fast default: yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=45, help="Keep short for demo usecase")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16, help="Use 8 if GPU RAM is limited")
    parser.add_argument("--device", default="0")
    parser.add_argument("--project", default="runs/usecase_models")
    parser.add_argument("--name", default="model_A_fast")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-best-as", default="model_A_usecase.pt")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"data.yaml not found: {data_path}")

    print("=" * 72)
    print("[USECASE MODEL A] fast clean-only baseline")
    print(f"  data   : {data_path}")
    print(f"  model  : {args.model}")
    print(f"  epochs : {args.epochs}")
    print(f"  device : {args.device}")
    print("  intent : good clean performance, weaker robustness")
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
        # intentionally mild augmentation -> cleaner fit, less adverse robustness
        hsv_h=0.010,
        hsv_s=0.40,
        hsv_v=0.20,
        degrees=5.0,
        translate=0.05,
        scale=0.20,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.40,
        mixup=0.0,
        copy_paste=0.0,
        close_mosaic=10,
        lr0=0.01,
        lrf=0.01,
        cos_lr=True,
    )

    save_best_weights(args.project, args.name, args.save_best_as)
    print("[NEXT] Register this checkpoint as candidate A in your model registry.")


if __name__ == "__main__":
    main()
