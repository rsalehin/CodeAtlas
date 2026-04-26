"""CodeAtlas Demo Launcher — single command, opens results in browser."""
import sys, webbrowser
from pathlib import Path
from main import pipeline

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_repo"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")

    is_url = target.startswith("http")
    print(f"\n{'='*60}")
    print(f"  CodeAtlas Demo")
    print(f"  Target: {target}")
    print(f"  Output: {out_dir.resolve()}")
    print(f"{'='*60}\n")

    if is_url:
        from main import clone_github
        import shutil
        repo_path = clone_github(target)
        try:
            G, communities = pipeline(repo_path, out_dir.resolve())
        finally:
            shutil.rmtree(repo_path, ignore_errors=True)
    else:
        G, communities = pipeline(Path(target).resolve(), out_dir.resolve())

    # Open in browser
    html_path = out_dir / "graph.html"
    if html_path.exists():
        webbrowser.open(str(html_path))
        print(f"\n  Opening {html_path} in your browser...")
    print("\n  Demo complete!")
