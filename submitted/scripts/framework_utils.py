
import csv
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_CLASS_NAMES = [
    "military_tank",
    "military_truck",
    "military_vehicle",
    "soldier",
]


PRESET_SCENARIOS = [
    {
        "scenario_id": "SCN_001",
        "weather": "clear",
        "time_of_day": "day",
        "target_density": "medium",
        "sensor_noise_level": 0.03,
        "adversarial_camouflage": False,
        "visibility_km": 10.0,
        "difficulty": "easy",
        "bucket": "clean_reference",
        "corruption_family": "none",
        "severity": 0,
        "safety_critical": False,
        "description": "Reference clean daytime scenario used as the primary clean baseline."
    },
    {
        "scenario_id": "SCN_002",
        "weather": "clear",
        "time_of_day": "day",
        "target_density": "low",
        "sensor_noise_level": 0.05,
        "adversarial_camouflage": False,
        "visibility_km": 9.0,
        "difficulty": "easy",
        "bucket": "clean_reference",
        "corruption_family": "none",
        "severity": 0,
        "safety_critical": False,
        "description": "Secondary clean reference scenario with sparse targets and minimal noise."
    },
    {
        "scenario_id": "SCN_003",
        "weather": "foggy",
        "time_of_day": "day",
        "target_density": "medium",
        "sensor_noise_level": 0.12,
        "adversarial_camouflage": False,
        "visibility_km": 4.5,
        "difficulty": "medium",
        "bucket": "operational",
        "corruption_family": "fog",
        "severity": 1,
        "safety_critical": False,
        "description": "Operational fog scenario representing common low-contrast daytime conditions."
    },
    {
        "scenario_id": "SCN_004",
        "weather": "rainy",
        "time_of_day": "day",
        "target_density": "high",
        "sensor_noise_level": 0.18,
        "adversarial_camouflage": False,
        "visibility_km": 4.0,
        "difficulty": "medium",
        "bucket": "operational",
        "corruption_family": "rain",
        "severity": 1,
        "safety_critical": False,
        "description": "Rain and clutter representative of regular field conditions."
    },
    {
        "scenario_id": "SCN_005",
        "weather": "hazy",
        "time_of_day": "dusk",
        "target_density": "medium",
        "sensor_noise_level": 0.20,
        "adversarial_camouflage": False,
        "visibility_km": 3.8,
        "difficulty": "medium",
        "bucket": "operational",
        "corruption_family": "haze",
        "severity": 1,
        "safety_critical": False,
        "description": "Dusk haze representative of reduced contrast and color fidelity."
    },
    {
        "scenario_id": "SCN_006",
        "weather": "clear",
        "time_of_day": "night",
        "target_density": "medium",
        "sensor_noise_level": 0.22,
        "adversarial_camouflage": False,
        "visibility_km": 2.2,
        "difficulty": "medium",
        "bucket": "operational",
        "corruption_family": "night",
        "severity": 1,
        "safety_critical": False,
        "description": "Nighttime operation under low illumination but without combined weather effects."
    },
    {
        "scenario_id": "SCN_007",
        "weather": "foggy",
        "time_of_day": "night",
        "target_density": "medium",
        "sensor_noise_level": 0.32,
        "adversarial_camouflage": True,
        "visibility_km": 1.5,
        "difficulty": "hard",
        "bucket": "adverse",
        "corruption_family": "fog+night+camo",
        "severity": 2,
        "safety_critical": True,
        "description": "Hard scenario combining night, fog, and camouflage."
    },
    {
        "scenario_id": "SCN_008",
        "weather": "rainy",
        "time_of_day": "dusk",
        "target_density": "high",
        "sensor_noise_level": 0.35,
        "adversarial_camouflage": True,
        "visibility_km": 1.8,
        "difficulty": "hard",
        "bucket": "adverse",
        "corruption_family": "rain+camo",
        "severity": 2,
        "safety_critical": False,
        "description": "Rain with clutter and camouflage under low-light dusk conditions."
    },
    {
        "scenario_id": "SCN_009",
        "weather": "snowy",
        "time_of_day": "night",
        "target_density": "medium",
        "sensor_noise_level": 0.36,
        "adversarial_camouflage": False,
        "visibility_km": 1.3,
        "difficulty": "hard",
        "bucket": "adverse",
        "corruption_family": "snow+night",
        "severity": 2,
        "safety_critical": False,
        "description": "Snow and night operation used as a robustness stress case."
    },
    {
        "scenario_id": "SCN_010",
        "weather": "foggy",
        "time_of_day": "day",
        "target_density": "high",
        "sensor_noise_level": 0.42,
        "adversarial_camouflage": True,
        "visibility_km": 1.1,
        "difficulty": "hard",
        "bucket": "adverse",
        "corruption_family": "fog+camo",
        "severity": 2,
        "safety_critical": False,
        "description": "Dense fog with camouflage and high scene density."
    },
    {
        "scenario_id": "SCN_011",
        "weather": "foggy",
        "time_of_day": "night",
        "target_density": "low",
        "sensor_noise_level": 0.55,
        "adversarial_camouflage": True,
        "visibility_km": 0.5,
        "difficulty": "extreme",
        "bucket": "critical",
        "corruption_family": "fog+night+noise+camo",
        "severity": 3,
        "safety_critical": True,
        "description": "Extreme mission-critical scenario with dense fog, darkness, high noise, and camouflage."
    },
    {
        "scenario_id": "SCN_012",
        "weather": "rainy",
        "time_of_day": "night",
        "target_density": "high",
        "sensor_noise_level": 0.62,
        "adversarial_camouflage": True,
        "visibility_km": 0.4,
        "difficulty": "extreme",
        "bucket": "critical",
        "corruption_family": "rain+night+noise+camo",
        "severity": 3,
        "safety_critical": True,
        "description": "Extreme mission-critical scenario with torrential rain, darkness, noise, and camouflage."
    },
]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        s = str(value).strip().replace('%', '')
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def dump_json(obj: Any, path: Path) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_csv_rows(path: Path) -> List[Dict[str, Any]]:
    if not Path(path).exists():
        return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv_rows(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def normalize_scenarios(scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for i, s in enumerate(scenarios, 1):
        item = dict(s)
        item['scenario_id'] = f"SCN_{i:03d}"
        item['sensor_noise_level'] = max(0.0, min(1.0, safe_float(item.get('sensor_noise_level', 0.1))))
        item['visibility_km'] = max(0.1, safe_float(item.get('visibility_km', 5.0)))
        item['adversarial_camouflage'] = bool(item.get('adversarial_camouflage', False))
        item.setdefault('difficulty', 'medium')
        item.setdefault('weather', 'clear')
        item.setdefault('time_of_day', 'day')
        item.setdefault('target_density', 'medium')
        item.setdefault('description', '')
        if 'bucket' not in item:
            diff = item['difficulty']
            item['bucket'] = {
                'easy': 'clean_reference',
                'medium': 'operational',
                'hard': 'adverse',
                'extreme': 'critical',
            }.get(diff, 'operational')
        if 'severity' not in item:
            item['severity'] = {'clean_reference': 0, 'operational': 1, 'adverse': 2, 'critical': 3}.get(item['bucket'], 1)
        item.setdefault('corruption_family', build_corruption_family(item))
        item.setdefault('safety_critical', item['bucket'] == 'critical')
        out.append(item)
    return out


def build_corruption_family(scn: Dict[str, Any]) -> str:
    parts = []
    weather = scn.get('weather', 'clear')
    tod = scn.get('time_of_day', 'day')
    if weather != 'clear':
        parts.append(weather.replace('y', ''))
    if tod in {'dusk', 'night'}:
        parts.append(tod)
    if scn.get('adversarial_camouflage'):
        parts.append('camo')
    if safe_float(scn.get('sensor_noise_level', 0.0)) >= 0.30:
        parts.append('noise')
    return '+'.join(parts) if parts else 'none'


def load_class_names(registry: Dict[str, Any]) -> List[str]:
    names = registry.get('class_names') or registry.get('names')
    if isinstance(names, dict):
        return [names[i] for i in sorted(names)]
    if isinstance(names, list) and names:
        return names
    return DEFAULT_CLASS_NAMES


def effect_night(img: Image.Image, strength: float) -> Image.Image:
    arr = np.array(img.convert('RGB'), dtype=np.float32)
    s = max(0.15, 1.0 - strength * 0.72)
    arr[:, :, 0] *= s * 0.82
    arr[:, :, 1] *= s * 0.90
    arr[:, :, 2] *= s * 1.02
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def effect_fog(img: Image.Image, intensity: float) -> Image.Image:
    fog = Image.new('RGB', img.size, (228, 231, 236))
    out = Image.blend(img.convert('RGB'), fog, min(0.78, intensity))
    radius = 0.5 + intensity * 2.6
    return out.filter(ImageFilter.GaussianBlur(radius=radius))


def effect_rain(img: Image.Image, intensity: float) -> Image.Image:
    out = img.copy().convert('RGB')
    w, h = out.size
    if intensity > 0.35:
        haze = Image.new('RGB', (w, h), (195, 200, 210))
        out = Image.blend(out, haze, min(0.30, (intensity - 0.35) * 0.65))
    draw = ImageDraw.Draw(out)
    n = int(w * h * intensity * 0.00075)
    for _ in range(n):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        draw.line([(x, y), (x - random.randint(1, 3), y + random.randint(8, 18))], fill=(160, 170, 190), width=1)
    blur_r = max(0.0, intensity * 0.9)
    if blur_r > 0.2:
        out = out.filter(ImageFilter.GaussianBlur(radius=blur_r))
    return out


def effect_snow(img: Image.Image, intensity: float) -> Image.Image:
    out = img.copy().convert('RGB')
    draw = ImageDraw.Draw(out)
    w, h = out.size
    n = int(120 + intensity * 280)
    for _ in range(n):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r = random.randint(1, max(1, int(1 + intensity * 4)))
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(250, 252, 255))
    if intensity > 0.3:
        snow_bg = Image.new('RGB', (w, h), (244, 247, 252))
        out = Image.blend(out, snow_bg, min(0.22, intensity * 0.22))
    return out


def effect_haze(img: Image.Image, intensity: float) -> Image.Image:
    haze = Image.new('RGB', img.size, (214, 196, 165))
    out = Image.blend(img.convert('RGB'), haze, min(0.52, intensity))
    return out.filter(ImageFilter.GaussianBlur(radius=max(0.2, intensity * 1.35)))


def effect_noise(img: Image.Image, level: float) -> Image.Image:
    sigma = level * 22.0
    if sigma < 0.5:
        return img.convert('RGB')
    arr = np.array(img.convert('RGB'), dtype=np.float32)
    arr += np.random.normal(0, sigma, arr.shape)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if level > 0.45:
        out = out.filter(ImageFilter.GaussianBlur(radius=min(1.0, level * 0.65)))
    return out


def effect_camouflage(img: Image.Image, intensity: float = 0.25) -> Image.Image:
    camo = [(78, 95, 58), (101, 87, 61), (55, 68, 42), (122, 108, 78), (68, 58, 45)]
    out = img.copy().convert('RGB')
    draw = ImageDraw.Draw(out)
    w, h = out.size
    n = int(8 + intensity * 18)
    for _ in range(n):
        cx = random.randint(0, w)
        cy = random.randint(0, h)
        rx = random.randint(max(4, int(w * 0.03)), max(8, int(w * 0.11)))
        ry = random.randint(max(4, int(h * 0.03)), max(8, int(h * 0.09)))
        draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=random.choice(camo))
    return Image.blend(img.convert('RGB'), out, min(0.40, intensity * 0.75))


def apply_scenario_to_image(img: Image.Image, scenario: Dict[str, Any]) -> Image.Image:
    out = img.convert('RGB')
    weather = scenario.get('weather', 'clear')
    tod = scenario.get('time_of_day', 'day')
    noise = safe_float(scenario.get('sensor_noise_level', 0.0))
    bucket = scenario.get('bucket', 'operational')
    severity = int(safe_float(scenario.get('severity', 1), 1))

    night_strength = {'day': 0.0, 'dusk': 0.32, 'night': 0.72}.get(tod, 0.0)
    if night_strength > 0:
        out = effect_night(out, night_strength)

    if weather == 'foggy':
        fog_intensity = {0: 0.12, 1: 0.28, 2: 0.48, 3: 0.64}.get(severity, 0.28)
        out = effect_fog(out, fog_intensity)
    elif weather == 'rainy':
        rain_intensity = {0: 0.10, 1: 0.32, 2: 0.55, 3: 0.72}.get(severity, 0.32)
        out = effect_rain(out, rain_intensity)
    elif weather == 'snowy':
        snow_intensity = {0: 0.12, 1: 0.28, 2: 0.45, 3: 0.60}.get(severity, 0.28)
        out = effect_snow(out, snow_intensity)
    elif weather == 'hazy':
        haze_intensity = {0: 0.10, 1: 0.22, 2: 0.35, 3: 0.42}.get(severity, 0.22)
        out = effect_haze(out, haze_intensity)

    if noise > 0:
        out = effect_noise(out, noise)
    if scenario.get('adversarial_camouflage', False):
        camo_intensity = {'operational': 0.18, 'adverse': 0.26, 'critical': 0.34}.get(bucket, 0.18)
        out = effect_camouflage(out, camo_intensity)

    return out


def summarize_by_rows(rows: List[Dict[str, Any]], bucket: str = None) -> Dict[str, float]:
    target = [r for r in rows if bucket is None or r.get('bucket') == bucket]
    if not target:
        return {'count': 0, 'precision': 0.0, 'recall': 0.0, 'map50': 0.0, 'map50_95': 0.0}
    n = len(target)
    return {
        'count': n,
        'precision': sum(safe_float(r.get('precision')) for r in target) / n,
        'recall': sum(safe_float(r.get('recall')) for r in target) / n,
        'map50': sum(safe_float(r.get('map50')) for r in target) / n,
        'map50_95': sum(safe_float(r.get('map50_95')) for r in target) / n,
    }


def top_failure_modes(rows: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    items = sorted(rows, key=lambda r: safe_float(r.get('map50'), 0.0))[:top_k]
    return [
        {
            'scenario_id': r.get('scenario_id', ''),
            'bucket': r.get('bucket', ''),
            'corruption_family': r.get('corruption_family', ''),
            'map50': round(safe_float(r.get('map50')), 4),
            'rpc_vs_clean': round(safe_float(r.get('relative_to_clean', 0.0)), 4),
        }
        for r in items
    ]
