"""
Build the 4-class Defense AI dataset from the original Kaggle 12-class dataset.

Rule (verified in E0 against the submission's evaluation labels and training label counts):
  - keep only boxes of original class 2 (military_tank)    -> 0
                                  3 (military_truck)   -> 1
                                  4 (military_vehicle) -> 2
                                  6 (soldier)          -> 3
  - drop all other boxes
  - drop images that have no remaining box

Usage (from the project folder):
  python revision\\scripts\\build_4cls_dataset.py --src <DATASET> --out revision\\data\\Defense_AI_4cls
"""

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import yaml

CLASS_MAP = {2: 0, 3: 1, 4: 2, 6: 3}
NAMES = {0: "military_tank", 1: "military_truck", 2: "military_vehicle", 3: "soldier"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def remap_label(path: Path) -> list[str]:
    """Return remapped label lines, keeping the original coordinate tokens unchanged."""
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            cls = int(float(p[0]))
            if cls in CLASS_MAP:
                out.append(" ".join([str(CLASS_MAP[cls])] + p[1:]))
    return out


def build_split(src: Path, out: Path, split: str) -> dict:
    src_img, src_lbl = src / split / "images", src / split / "labels"
    out_img, out_lbl = out / split / "images", out / split / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    images = sorted(p for p in src_img.iterdir() if p.suffix.lower() in IMG_EXTS)
    boxes, imgs_per_class = Counter(), Counter()
    kept = no_label = no_target = 0
    for img in images:
        lbl = src_lbl / f"{img.stem}.txt"
        if not lbl.exists():
            no_label += 1
            continue
        lines = remap_label(lbl)
        if not lines:
            no_target += 1
            continue
        shutil.copy2(img, out_img / img.name)
        with open(out_lbl / lbl.name, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        classes = [int(l.split()[0]) for l in lines]
        boxes.update(classes)
        imgs_per_class.update(set(classes))
        kept += 1

    return {
        "source_images": len(images),
        "images": kept,
        "skipped_no_label_file": no_label,
        "skipped_no_target_box": no_target,
        "boxes_per_class": {NAMES[k]: boxes[k] for k in sorted(NAMES)},
        "images_per_class": {NAMES[k]: imgs_per_class[k] for k in sorted(NAMES)},
        "total_boxes": sum(boxes.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Original 12-class dataset root (train/val/test)")
    parser.add_argument("--out", required=True, help="Output root for the 4-class dataset")
    parser.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    args = parser.parse_args()

    src, out = Path(args.src), Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"output directory is not empty: {out}")

    stats = {"source": str(src.resolve()), "class_map_original_to_new": {str(k): v for k, v in CLASS_MAP.items()}, "splits": {}}
    for split in args.splits:
        stats["splits"][split] = build_split(src, out, split)
        print(f"[OK] {split}: {json.dumps(stats['splits'][split], ensure_ascii=False)}")

    root = out.resolve()
    data = {"path": str(root), "train": "train/images", "val": "val/images", "test": "test/images", "nc": 4, "names": NAMES}
    with open(out / "data.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    with open(out / "build_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"[OK] data.yaml -> {(out / 'data.yaml').resolve()}")


if __name__ == "__main__":
    main()
