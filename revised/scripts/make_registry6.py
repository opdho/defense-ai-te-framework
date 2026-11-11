"""Build revision/registry_6.json from the existing registries and verify each weight's MD5
against the registry value and against RESULTS_SUMMARY.md. Fails if the output already exists."""
import hashlib
import json
from pathlib import Path

OUT = Path("revision/registry_6.json")
if OUT.exists():
    raise SystemExit(f"[ERROR] {OUT} exists")


def models_of(name):
    return {m["model_id"]: m for m in json.loads(Path(f"revision/{name}.json").read_text(encoding="utf-8"))["models"]}


ab, retrain, x22 = models_of("registry_AB"), models_of("registry_retrain"), models_of("registry_2x2")
models = [ab["model_A"], ab["model_B"], retrain["model_A_rep"], retrain["model_B_rep"], retrain["model_C_clean"], x22["model_D"]]
summary_text = Path("revision/RESULTS_SUMMARY.md").read_text(encoding="utf-8")

ok = True
for m in models:
    actual = hashlib.md5(Path(m["weights"]).read_bytes()).hexdigest()
    in_summary = actual in summary_text
    good = actual == m["md5"] and in_summary
    ok &= good
    print(f"{m['model_id']:<14} actual={actual} registry_match={actual == m['md5']} in_RESULTS_SUMMARY={in_summary}")
if not ok:
    raise SystemExit("[ERROR] MD5 check failed; registry_6.json not written")

OUT.write_text(json.dumps({"registry_name": "revision_6_models_uninterrupted_training",
                           "class_names": ["military_tank", "military_truck", "military_vehicle", "soldier"],
                           "models": models}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] {OUT}")
