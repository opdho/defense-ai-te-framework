import argparse
from pathlib import Path

from framework_utils import DEFAULT_CLASS_NAMES, dump_json


def parse_names(raw):
    if not raw:
        return DEFAULT_CLASS_NAMES
    return [x.strip() for x in raw.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(description='Create a registry JSON for the framework demo.')
    parser.add_argument('--weights-a', required=True)
    parser.add_argument('--weights-b', required=True)
    parser.add_argument('--out', default='model_registry.json')
    parser.add_argument('--class-names', default=','.join(DEFAULT_CLASS_NAMES))
    args = parser.parse_args()

    registry = {
        'registry_name': 'framework_usecase_demo',
        'class_names': parse_names(args.class_names),
        'models': [
            {
                'model_id': 'model_A',
                'display_name': 'Model A (general but fragile)',
                'weights': str(Path(args.weights_a)),
                'notes': 'Use-case model expected to perform well on clean reference but degrade under corruption scenarios.',
            },
            {
                'model_id': 'model_B',
                'display_name': 'Model B (general and robust)',
                'weights': str(Path(args.weights_b)),
                'notes': 'Use-case model expected to maintain performance across corruption scenarios.',
            },
        ],
    }
    dump_json(registry, Path(args.out))
    print(f'[OK] registry written -> {args.out}')


if __name__ == '__main__':
    main()
