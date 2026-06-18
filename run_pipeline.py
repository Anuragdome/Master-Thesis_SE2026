"""
run_pipeline.py
===============
Entry point for the Knowledge Graph Pipeline.

Just run:
    python run_pipeline.py

Options:
    python run_pipeline.py --input path/to/docs
    python run_pipeline.py --no-neo4j
    python run_pipeline.py --help
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("pipeline.log", mode="w"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Knowledge Graph Pipeline — build a KG from unstructured documents"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=None,
        help="Directory of input documents (default: data/raw/)",
    )
    parser.add_argument(
        "--no-neo4j",
        action="store_true",
        help="Skip Neo4j and export to files only",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "gemini"],
        default=None,
        help="Override LLM provider from settings",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model name from settings",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    # Load config and apply CLI overrides
    import config.settings as cfg
    if args.no_neo4j:
        cfg.NEO4J_ENABLED = False
    if args.provider:
        cfg.LLM_PROVIDER = args.provider
    if args.model:
        cfg.MODEL_NAME = args.model

    # Run the pipeline
    from src.pipeline import Pipeline
    pipeline = Pipeline(config_module=cfg)
    results = pipeline.run(input_dir=args.input)

    if results:
        print("\nDone! Check data/output/ for results.")
    else:
        print("\nPipeline finished with errors — check pipeline.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
