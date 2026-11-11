import argparse
import json
import re
from pathlib import Path

import requests

from framework_utils import PRESET_SCENARIOS, dump_json, normalize_scenarios


SYSTEM_PROMPT = """You are a defense AI T&E scenario planner.
Output JSON array only. No markdown, no prose, no code block.
Each scenario must contain:
weather(clear|foggy|rainy|snowy|hazy),
time_of_day(day|dusk|night),
target_density(low|medium|high),
sensor_noise_level(0.0~1.0),
adversarial_camouflage(boolean),
visibility_km(0.1~10.0),
difficulty(easy|medium|hard|extreme),
description(string).
Generate a balanced mix across easy / medium / hard / extreme.
The first two scenarios should be clean reference scenarios.
Avoid GPS jamming and any class list in the output.
"""


def call_ollama(host: str, model: str, num: int):
    user = (
        f"Generate {num} scenario records for automated scenario-based object detection T&E. "
        "The output is for corruption robustness and deployment gate evaluation."
    )
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "weather": {"type": "string"},
                "time_of_day": {"type": "string"},
                "target_density": {"type": "string"},
                "sensor_noise_level": {"type": "number"},
                "adversarial_camouflage": {"type": "boolean"},
                "visibility_km": {"type": "number"},
                "difficulty": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": [
                "weather",
                "time_of_day",
                "target_density",
                "sensor_noise_level",
                "adversarial_camouflage",
                "visibility_km",
                "difficulty",
                "description",
            ],
        },
    }
    r = requests.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "stream": False,
            "think": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        },
        timeout=180,
    )
    r.raise_for_status()
    raw = r.json()["message"]["content"].strip()
    raw = re.sub(r"^```[a-zA-Z0-9_\-]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="Generate scenario manifests for automated T&E.")
    parser.add_argument("--mode", choices=["preset", "llm"], default="preset")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--num", type=int, default=12)
    parser.add_argument("--out", default="scenario_manifest.json")
    args = parser.parse_args()

    if args.mode == "preset":
        scenarios = PRESET_SCENARIOS[: args.num]
        print("[INFO] preset mode: built-in scenario set selected")
    else:
        try:
            scenarios = call_ollama(args.host, args.model, args.num)
            print(f"[INFO] LLM scenario generation succeeded: {args.model}")
        except Exception as e:
            print(f"[WARN] LLM scenario generation failed ({e}). Falling back to preset.")
            scenarios = PRESET_SCENARIOS[: args.num]

    scenarios = normalize_scenarios(scenarios)
    dump_json(scenarios, Path(args.out))

    print(f"\n[OK] {len(scenarios)} scenarios written -> {args.out}")
    print(f"\n{'ID':<10} {'bucket':<16} {'weather':<8} {'time':<6} {'noise':>6} {'camo':>5} {'sev':>4}")
    print("-" * 72)
    for s in scenarios:
        print(
            f"{s['scenario_id']:<10} {s['bucket']:<16} {s['weather']:<8} {s['time_of_day']:<6} "
            f"{s['sensor_noise_level']:>6.2f} {'Y' if s['adversarial_camouflage'] else 'N':>5} {s['severity']:>4}"
        )

    print("\n[NEXT] python 02_generate_ms_eval_dataset.py --scenarios scenario_manifest.json ...")


if __name__ == "__main__":
    main()
