"""
Build the registries used after the E4 retrain (md5 of each weight file is computed here):
  revision/registry_retrain.json : A_rep, C_clean, B_rep (retrained on this laptop, workers 4, single run each)
  revision/registry_7.json       : A, B (submission weights), C, D (revision weights), A_rep, B_rep, C_clean
Fails if any weight file is missing.

Usage (from D:\park\test5):
  python revision\scripts\make_registries.py --out-retrain revision\registry_retrain.json --out-7 revision\registry_7.json
"""

import argparse
import hashlib
import json
from pathlib import Path

RETRAIN = [
    ("model_A_rep", "Candidate A_rep (YOLO11n, base recipe, retrained)", "D:/park/test5/revision/weights/model_A_rep.pt",
     "Revision retrain (this laptop, 2026-10-29). Same as A: yolo11n.pt, 4-class train only, 01 script (epochs 45, weak augmentation), seed 42; --workers 4."),
    ("model_C_clean", "Candidate C_clean (YOLO11n, robust recipe, retrained)", "D:/park/test5/revision/weights/model_C_clean.pt",
     "Revision retrain (this laptop, 2026-10-29). Same as C but one uninterrupted run: yolo11n.pt, 4-class train + augmented_model_B, 02 script (epochs 70, strong augmentation), seed 42; --workers 4."),
    ("model_B_rep", "Candidate B_rep (YOLO11s, robust recipe, retrained)", "D:/park/test5/revision/weights/model_B_rep.pt",
     "Revision retrain (this laptop, 2026-10-29). Same as B: yolo11s.pt, 4-class train + augmented_model_B, 02 script (epochs 70, strong augmentation), seed 42; --workers 4."),
]


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="revision/registry_2x2.json")
    p.add_argument("--out-retrain", required=True)
    p.add_argument("--out-7", required=True)
    a = p.parse_args()

    base = json.loads(Path(a.base).read_text(encoding="utf-8"))
    retrain = []
    for mid, name, w, notes in RETRAIN:
        if not Path(w).is_file():
            raise SystemExit(f"[ERROR] missing weights: {w}")
        retrain.append({"model_id": mid, "display_name": name, "weights": w, "md5": md5(w), "notes": notes})
    for m in base["models"]:
        if md5(m["weights"]) != m["md5"]:
            raise SystemExit(f"[ERROR] md5 mismatch: {m['weights']}")

    reg_r = {"registry_name": "revision_retrain_A_rep_C_clean_B_rep", "class_names": base["class_names"], "models": retrain}
    by_id = {m["model_id"]: m for m in base["models"] + retrain}
    order = ["model_A", "model_B", "model_C", "model_D", "model_A_rep", "model_B_rep", "model_C_clean"]
    reg_7 = {"registry_name": "revision_7_models", "class_names": base["class_names"], "models": [by_id[k] for k in order]}
    Path(a.out_retrain).write_text(json.dumps(reg_r, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(a.out_7).write_text(json.dumps(reg_7, ensure_ascii=False, indent=2), encoding="utf-8")
    for m in retrain:
        print(m["model_id"], m["md5"])
    print(f"[OK] {a.out_retrain}  {a.out_7}")


if __name__ == "__main__":
    main()
