"""Verdict command-line interface."""
import argparse
import sys

from .engine import answer, debate


def main():
    parser = argparse.ArgumentParser(prog="verdict", description="Free-first local AI developer companion")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("ask", "explain", "debug", "review"):
        p = sub.add_parser(name)
        p.add_argument("question", nargs="?", help="Question, code, or error text; stdin is used when omitted")
        p.add_argument("--allow-cloud", action="store_true", help="Explicitly authorize configured cloud fallback for this request")
    p = sub.add_parser("decide")
    p.add_argument("question")
    p.add_argument("--allow-cloud", action="store_true")
    sub.add_parser("mcp")
    args = parser.parse_args()

    if args.command == "mcp":
        from .mcp_server import main as run_mcp
        run_mcp()
        return

    prompt = args.question if getattr(args, "question", None) else sys.stdin.read()
    if not prompt.strip():
        parser.error("Provide a question or pipe content through stdin.")
    result = (debate(prompt, args.allow_cloud) if args.command == "decide"
              else answer(prompt, args.command, args.allow_cloud))
    print(result)


if __name__ == "__main__":
    main()
