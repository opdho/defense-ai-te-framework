import argparse
import shutil
from pathlib import Path

import yaml
from PIL import Image

from framework_utils import DEFAULT_CLASS_NAMES, apply_scenario_to_image, dump_json, ensure_dir, load_json


def copy_labels(src_labels: Path, dst_labels: Path) -> int:
    n = 0
    for p in sorted(src_labels.glob('*.txt')):
        shutil.copy2(p, dst_labels / p.name)
        n += 1
    return n


def parse_names(raw: str):
    if not raw:
        return DEFAULT_CLASS_NAMES
    return [x.strip() for x in raw.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(description='Create scenario-specific M&S evaluation datasets from real validation images.')
    parser.add_argument('--scenarios', required=True)
    parser.add_argument('--val-images', required=True)
    parser.add_argument('--val-labels', required=True)
    parser.add_argument('--output', default='dataset/ms_eval_framework')
    parser.add_argument('--yaml-dir', default='dataset_yaml_framework')
    parser.add_argument('--class-names', default=','.join(DEFAULT_CLASS_NAMES))
    args = parser.parse_args()

    scenarios = load_json(Path(args.scenarios))
    src_images = Path(args.val_images)
    src_labels = Path(args.val_labels)
    out_root = ensure_dir(Path(args.output))
    yaml_dir = ensure_dir(Path(args.yaml_dir))
    class_names = parse_names(args.class_names)
    name_map = {i: name for i, name in enumerate(class_names)}

    if not src_images.exists() or not src_labels.exists():
        raise FileNotFoundError('Validation images/labels were not found.')

    generated_meta = []
    for scn in scenarios:
        sid = scn['scenario_id']
        img_dir = ensure_dir(out_root / sid / 'images')
        lbl_dir = ensure_dir(out_root / sid / 'labels')

        generated = 0
        for img_path in sorted(src_images.iterdir()):
            if img_path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.bmp'}:
                continue
            img = Image.open(img_path).convert('RGB')
            out = apply_scenario_to_image(img, scn)
            out.save(img_dir / img_path.name)
            generated += 1

        copied = copy_labels(src_labels, lbl_dir)
        yaml_content = {
            'path': '.',
            'train': str(src_images.parent.parent / 'train' / 'images'),
            'val': str(img_dir.resolve()),
            'nc': len(class_names),
            'names': name_map,
        }
        yaml_path = yaml_dir / f'data_{sid}.yaml'
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(yaml_content, f, allow_unicode=True, sort_keys=False)

        generated_meta.append({
            **scn,
            'generated_images': generated,
            'copied_labels': copied,
            'yaml': str(yaml_path),
        })
        print(
            f"[{sid}] bucket={scn['bucket']:<16} weather={scn['weather']:<7} time={scn['time_of_day']:<5} "
            f"noise={scn['sensor_noise_level']:.2f} camo={'Y' if scn['adversarial_camouflage'] else 'N'} "
            f"images={generated} labels={copied}"
        )

    dump_json(generated_meta, Path('scenario_metadata_framework.json'))
    print('\n[OK] Scenario evaluation datasets created')
    print(f'  datasets: {out_root.resolve()}')
    print(f'  yamls   : {yaml_dir.resolve()}')
    print('\n[NEXT] python 03_evaluate_registry.py --registry model_registry.json --yaml-dir ... --scenarios scenario_metadata_framework.json')


if __name__ == '__main__':
    main()
