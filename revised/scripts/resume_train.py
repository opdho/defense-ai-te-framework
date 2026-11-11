"""
Resume an interrupted Ultralytics training run from its last.pt.

All training args are restored from the checkpoint (check_resume in ultralytics 8.4.21);
only the args Ultralytics allows on resume are overridden here (workers).
Used for E4 model C: the original run stalled at "Closing dataloader mosaic" after epoch 60
with RAM exhausted by unreleased dataloader workers, so it is resumed with workers 4 instead of 8.

Usage (from D:\\park\\test5):
  python revision\\scripts\\resume_train.py --last revision\\runs\\model_C_n_robust\\weights\\last.pt --workers 4 --save-best-as revision\\weights\\model_C_n_robust.pt
"""

import argparse
import hashlib
import shutil
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--last", required=True, help="last.pt of the interrupted run")
    p.add_argument("--workers", type=int, required=True)
    p.add_argument("--save-best-as", required=True)
    a = p.parse_args()

    last = Path(a.last).resolve()
    print(f"[RESUME] {last}  workers={a.workers}")
    model = YOLO(str(last))
    model.train(resume=True, workers=a.workers)

    best = last.parent / "best.pt"
    if not best.exists():
        print(f"[WARN] best.pt not found: {best}")
        return
    dst = Path(a.save_best_as)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, dst)
    print(f"[OK] copied best weights -> {dst.resolve()}  md5={hashlib.md5(dst.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
