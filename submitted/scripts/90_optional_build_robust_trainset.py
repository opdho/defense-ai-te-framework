import argparse
import random
import shutil
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter


def add_noise(img, sigma):
    arr = np.array(img.convert('RGB'), dtype=np.float32)
    arr += np.random.normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def night(img):
    arr = np.array(img.convert('RGB'), dtype=np.float32)
    arr[:, :, 0] *= 0.42
    arr[:, :, 1] *= 0.50
    arr[:, :, 2] *= 0.66
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def fog(img):
    fog_layer = Image.new('RGB', img.size, (228, 230, 235))
    out = Image.blend(img.convert('RGB'), fog_layer, 0.35)
    return out.filter(ImageFilter.GaussianBlur(radius=1.2))


def rain(img):
    out = img.copy().convert('RGB')
    draw = ImageDraw.Draw(out)
    w, h = out.size
    for _ in range(int(w * h * 0.00045)):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        draw.line([(x, y), (x - 2, y + random.randint(8, 16))], fill=(160, 170, 190), width=1)
    return out.filter(ImageFilter.GaussianBlur(radius=0.6))


def haze(img):
    layer = Image.new('RGB', img.size, (214, 196, 165))
    out = Image.blend(img.convert('RGB'), layer, 0.22)
    return out.filter(ImageFilter.GaussianBlur(radius=0.8))


def camo(img):
    colors = [(78, 95, 58), (101, 87, 61), (55, 68, 42), (122, 108, 78)]
    out = img.copy().convert('RGB')
    draw = ImageDraw.Draw(out)
    w, h = out.size
    for _ in range(10):
        cx = random.randint(0, w)
        cy = random.randint(0, h)
        rx = random.randint(max(4, int(w * 0.03)), max(8, int(w * 0.10)))
        ry = random.randint(max(4, int(h * 0.03)), max(8, int(h * 0.10)))
        draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=random.choice(colors))
    return Image.blend(img.convert('RGB'), out, 0.18)


AUGS = {
    'night': night,
    'fog': fog,
    'rain': rain,
    'noise': lambda x: add_noise(x, 18),
    'haze': haze,
    'camo': camo,
}


def main():
    parser = argparse.ArgumentParser(description='Optional helper: create a compact robust trainset for demo Model B.')
    parser.add_argument('--src-images', required=True)
    parser.add_argument('--src-labels', required=True)
    parser.add_argument('--output', default='augmented_demo_B')
    parser.add_argument('--per-type', type=int, default=120)
    parser.add_argument('--base-data-yaml', default='data.yaml')
    args = parser.parse_args()

    src_images = Path(args.src_images)
    src_labels = Path(args.src_labels)
    out = Path(args.output)
    out_images = out / 'train' / 'images'
    out_labels = out / 'train' / 'labels'
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    image_paths = [p for p in sorted(src_images.iterdir()) if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp'}]
    if not image_paths:
        raise FileNotFoundError('No training images were found.')

    for img_path in image_paths:
        shutil.copy2(img_path, out_images / img_path.name)
        label_path = src_labels / f'{img_path.stem}.txt'
        if label_path.exists():
            shutil.copy2(label_path, out_labels / label_path.name)

    for aug_name, aug_fn in AUGS.items():
        for i, img_path in enumerate(random.sample(image_paths, min(args.per_type, len(image_paths)))):
            img = Image.open(img_path).convert('RGB')
            out_img = aug_fn(img)
            out_name = f'{img_path.stem}_{aug_name}_{i:04d}{img_path.suffix.lower()}'
            out_img.save(out_images / out_name)
            label_path = src_labels / f'{img_path.stem}.txt'
            if label_path.exists():
                shutil.copy2(label_path, out_labels / f'{Path(out_name).stem}.txt')
        print(f'[OK] {aug_name}: generated up to {args.per_type} images')

    with open(args.base_data_yaml, 'r', encoding='utf-8') as f:
        base = yaml.safe_load(f)
    base['train'] = str((out / 'train' / 'images').resolve())
    out_yaml = out / 'data_demo_B.yaml'
    with open(out_yaml, 'w', encoding='utf-8') as f:
        yaml.safe_dump(base, f, allow_unicode=True, sort_keys=False)

    print(f'\n[OK] robust demo trainset written -> {out.resolve()}')
    print(f'[NEXT] python 92_optional_train_demo_model_B.py --data {out_yaml}')


if __name__ == '__main__':
    main()
