import argparse
from pathlib import Path

from .experiments import run_research


def main():
    parser = argparse.ArgumentParser(description="Reproduce the frozen industry-signal research protocol")
    parser.add_argument("--root", default=".", help="Repository root containing research_protocol.json")
    parser.add_argument("--output", default="results/reproduced")
    parser.add_argument("--profile", choices=["quick", "full"], default="full")
    parser.add_argument("--allow-revised-data", action="store_true")
    args = parser.parse_args()
    run_research(Path(args.root), Path(args.output), args.profile, args.allow_revised_data)


if __name__ == "__main__":
    main()

