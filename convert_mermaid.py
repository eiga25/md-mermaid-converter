#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple
from datetime import datetime


# Constants
MERMAID_BLOCK_RE = re.compile(
	r"^```mermaid\s*\n(.*?)\n```\s*",
	re.DOTALL | re.MULTILINE,
)
MARKER_PREFIX = "<!-- mmd-rendered:"
DEFAULT_OUT_DIR = "docs/_assets/mermaid"
LOOKAHEAD_REPLACE = 600
LOOKAHEAD_APPEND = 400


def which(cmd: str) -> str | None:
	"""Wrapper for shutil.which to find command in PATH."""
	return shutil.which(cmd)


def get_mmdc_cmd() -> list[str] | None:
	"""Find mmdc (Mermaid CLI) command, checking multiple locations.
	
	Priority:
	1. MERMAID_CLI environment variable
	2. System PATH
	3. Windows APPDATA/npm folder
	"""
	candidates: list[str] = []
	
	# Check environment variable first (highest priority)
	env_cli = os.environ.get("MERMAID_CLI")
	if env_cli and os.path.exists(env_cli):
		return [env_cli]
	
	# Check PATH
	for name in ("mmdc", "mmdc.cmd"):
		exe = which(name)
		if exe:
			candidates.append(exe)
	
	# Windows-specific: check APPDATA/npm
	if platform.system() == "Windows":
		appdata = os.environ.get("APPDATA")
		if appdata:
			cand = os.path.join(appdata, "npm", "mmdc.cmd")
			if os.path.exists(cand):
				candidates.append(cand)
	
	if not candidates:
		return None
	return [candidates[0]]


def ensure_mmdc_available() -> bool:
	"""Check if mmdc command is available and executable."""
	cmd = get_mmdc_cmd()
	if not cmd:
		return False
	try:
		subprocess.run(
			cmd + ["-v"], 
			stdout=subprocess.DEVNULL, 
			stderr=subprocess.DEVNULL, 
			check=False,
			timeout=5
		)
		return True
	except (OSError, subprocess.TimeoutExpired):
		return False


def hash_text(s: str) -> str:
	"""Generate a short hash for content-based filename uniqueness."""
	return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def find_mermaid_blocks(md_text: str) -> List[Tuple[Tuple[int, int], str]]:
	"""Find all Mermaid code blocks in Markdown text.
	
	Returns:
		List of ((start_pos, end_pos), code_content) tuples
	"""
	blocks: List[Tuple[Tuple[int, int], str]] = []
	for m in MERMAID_BLOCK_RE.finditer(md_text):
		blocks.append(((m.start(), m.end()), m.group(1)))
	return blocks


def render_mermaid(code: str, out_path: Path, fmt: str = "png", background: str = "transparent") -> None:
	"""Render Mermaid code to image file using mmdc CLI.
	
	Args:
		code: Mermaid diagram source code
		out_path: Output file path (extension will be adjusted based on fmt)
		fmt: Output format ('png' or 'svg')
		background: Background color (default: 'transparent')
		
	Raises:
		RuntimeError: If mmdc is not found or rendering fails
	"""
	out_path.parent.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory() as td:
		src = Path(td) / "diagram.mmd"
		src.write_text(code, encoding="utf-8")
		base_cmd = get_mmdc_cmd()
		if not base_cmd:
			raise RuntimeError(
				"mmdc not found; ensure Mermaid CLI is installed and on PATH or set MERMAID_CLI"
			)
		
		# Adjust output path and command for format
		if fmt.lower() == "svg":
			out_path = out_path.with_suffix(".svg")
		
		cmd = base_cmd + ["-i", str(src), "-o", str(out_path), "-b", background]
		proc = subprocess.run(cmd, capture_output=True, text=True)
		if proc.returncode != 0:
			raise RuntimeError(f"mmdc failed: {proc.stderr.strip() or proc.stdout.strip()}")


def replace_blocks_with_images(
	md_text: str,
	md_file: Path,
	images_written: List[Tuple[Tuple[int, int], Path]],
	image_paths_rel: List[str],
) -> str:
	"""Replace Mermaid code blocks with image links.
	
	Skips existing markers or image links to avoid duplication.
	"""
	parts: List[str] = []
	last = 0
	
	for ((start, end), out_path), rel in zip(images_written, image_paths_rel):
		parts.append(md_text[last:start])
		lookahead = md_text[end:end + LOOKAHEAD_REPLACE]
		skip_extra = 0
		image_name = out_path.name
		
		# Check for existing marker comment
		marker_idx = lookahead.find(MARKER_PREFIX + image_name)
		if marker_idx != -1:
			end_marker = lookahead.find("-->", marker_idx)
			if end_marker != -1:
				end_after = end_marker + 3
				if end_after < len(lookahead) and lookahead[end_after:end_after+1] == "\n":
					end_after += 1
				skip_extra = end_after
		# Check for existing image link
		else:
			m = re.search(r"^\s*!\[[^\]]*\]\([^\)]*mermaid[^\)]*\)\s*\n?", lookahead, re.MULTILINE)
			if m and m.start() == 0:
				skip_extra = m.end()

		alt = md_file.stem + " diagram"
		parts.append(f"![{alt}]({rel})\n")
		last = end + skip_extra
		
	parts.append(md_text[last:])
	return "".join(parts)


def add_images_after_blocks(
	md_text: str,
	md_file: Path,
	images_written: List[Tuple[Tuple[int, int], Path]],
	image_paths_rel: List[str],
) -> str:
	"""Append image links after Mermaid code blocks (keep source).
	
	Skips if image link or marker already exists.
	"""
	parts: List[str] = []
	last = 0
	
	for ((start, end), out_path), rel in zip(images_written, image_paths_rel):
		parts.append(md_text[last:end])
		image_name = out_path.name
		lookahead = md_text[end:end + LOOKAHEAD_APPEND]
		
		# Skip if already rendered
		if image_name in lookahead or MARKER_PREFIX in lookahead:
			last = end
			continue
		
		alt = md_file.stem + " diagram"
		parts.append(f"\n![{alt}]({rel})\n{MARKER_PREFIX}{image_name} -->\n")
		last = end
		
	parts.append(md_text[last:])
	return "".join(parts)


def process_file(
	md_file: Path,
	out_dir: Path | None,
	images_dir_rel: str | None,
	fmt: str,
	mode: str,
	dry_run: bool,
	backup: bool,
	force: bool,
) -> Tuple[int, int]:
	"""Process a Markdown file to render Mermaid diagrams.
	
	Args:
		md_file: Path to Markdown file
		out_dir: Global output directory (used if images_dir_rel is None)
		images_dir_rel: Per-file images directory relative to MD file
		fmt: Output format ('png' or 'svg')
		mode: Processing mode ('export_only', 'render_replace', 'render_keep')
		dry_run: If True, don't actually render or modify files
		backup: If True, create backup before modifying MD file
		force: If True, re-render even if output exists
		
	Returns:
		(blocks_found, images_written) tuple
	"""
	text = md_file.read_text(encoding="utf-8")
	blocks = find_mermaid_blocks(text)
	if not blocks:
		return (0, 0)

	images_written: List[Tuple[Tuple[int, int], Path]] = []
	image_paths_rel: List[str] = []

	if images_dir_rel is not None:
		if images_dir_rel.strip().lower() == "per-file":
			images_base = (md_file.parent / f"{md_file.stem}_images").resolve()
			rel_base_from_md = Path(f"{md_file.stem}_images")
		elif images_dir_rel.strip() == "" or images_dir_rel.strip() == ".":
			images_base = md_file.parent.resolve()
			rel_base_from_md = Path(".")
		else:
			images_base = (md_file.parent / images_dir_rel).resolve()
			rel_base_from_md = Path(images_dir_rel)
	else:
		default_out = Path.cwd() / DEFAULT_OUT_DIR
		images_base = (out_dir or default_out).resolve()
		rel_base_from_md = Path(os.path.relpath(images_base, md_file.parent))

	for idx, ((start, end), code) in enumerate(blocks, start=1):
		h = hash_text(code)
		ext = ".svg" if fmt.lower() == "svg" else ".png"
		image_name = f"{md_file.stem}-mermaid-{idx}-{h}{ext}"
		out_path = images_base / image_name
		rel_path = (rel_base_from_md / image_name).as_posix()

		if dry_run:
			print(f"[DRY] {md_file} -> {out_path}")
			images_written.append(((start, end), out_path))
			image_paths_rel.append(rel_path)
		else:
			if out_path.exists() and not force:
				print(f"[SKIP] {md_file.name}: exists {out_path.name}")
				images_written.append(((start, end), out_path))
				image_paths_rel.append(rel_path)
				continue
			try:
				render_mermaid(code, out_path, fmt=fmt)
				print(f"[OK ] {md_file.name}: wrote {out_path}")
				images_written.append(((start, end), out_path))
				image_paths_rel.append(rel_path)
			except (RuntimeError, OSError) as e:
				msg = str(e).strip()
				print(f"[ERR] {md_file.name} block#{idx} failed: {msg}", file=sys.stderr)

	if mode == "render_replace":
		new_text = replace_blocks_with_images(text, md_file, images_written, image_paths_rel)
		if not dry_run and new_text != text:
			if backup:
				_create_backup(md_file)
			md_file.write_text(new_text, encoding="utf-8", newline="\n")
			print(f"[MD ] updated {md_file}")
	elif mode == "render_keep":
		new_text = add_images_after_blocks(text, md_file, images_written, image_paths_rel)
		if new_text != text and not dry_run:
			if backup:
				_create_backup(md_file)
			md_file.write_text(new_text, encoding="utf-8", newline="\n")
			print(f"[MD ] appended image links {md_file}")

	return (len(blocks), len(images_written))


def iter_markdown_files(path: Path, recursive: bool) -> Iterable[Path]:
	"""Iterate over Markdown files in given path.
	
	Args:
		path: File or directory path
		recursive: Whether to search subdirectories
		
	Yields:
		Path objects for Markdown files (.md, .markdown)
	"""
	if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
		yield path
	elif path.is_dir():
		pattern = "**/*.md" if recursive else "*.md"
		for p in path.glob(pattern):
			if p.is_file():
				yield p


def main(argv: List[str]) -> int:
	"""Main CLI entry point.
	
	Args:
		argv: Command-line arguments
		
	Returns:
		Exit code (0 for success, 2 for error)
	"""
	p = argparse.ArgumentParser(description="Convert Mermaid code blocks in Markdown files to images using mmdc")
	p.add_argument("-i", "--input", required=True, help="Markdown file or folder to process")
	p.add_argument("-r", "--recursive", action="store_true", help="Recurse into subfolders when input is a folder")
	p.add_argument("-o", "--out-dir", default=None, help="Absolute or repo-relative folder to write images (default: docs/_assets/mermaid)")
	p.add_argument("--images-dir", default=None, help="Per-file images subfolder (relative to MD file), e.g. _mermaid | '.' | per-file (=> [name]_images)")
	p.add_argument("-f", "--format", choices=["png", "svg"], default="png", help="Image format (default: png)")
	mode_group = p.add_mutually_exclusive_group()
	mode_group.add_argument("--render", action="store_true", help="Render diagrams and update Markdown (with or without keeping source)")
	mode_group.add_argument("--export", action="store_true", help="Export images only; do not modify Markdown")
	p.add_argument("--keep-source", action="store_true", help="With --render, keep Mermaid source blocks and append image links after them")
	p.add_argument("--backup", action="store_true", help="Create a timestamped .bak copy of the Markdown file before modifying it")
	p.add_argument("--force", action="store_true", help="Force re-render even if target image already exists")
	p.add_argument("--replace", action="store_true", help=argparse.SUPPRESS)
	p.add_argument("--add", action="store_true", help=argparse.SUPPRESS)
	p.add_argument("--dry-run", action="store_true", help="Print planned actions without rendering or writing")

	args = p.parse_args(argv)

	in_path = Path(args.input)
	out_dir = Path(args.out_dir).resolve() if args.out_dir else None
	images_dir_rel = args.images_dir

	op_mode: str | None = None
	if args.render:
		op_mode = "render_keep" if args.keep_source else "render_replace"
	elif args.export:
		op_mode = "export_only"
	elif args.replace or args.add:
		if args.replace and args.add:
			print("ERROR: --replace and --add are mutually exclusive", file=sys.stderr)
			return 2
		op_mode = "render_keep" if args.add else "render_replace"
	else:
		op_mode = "export_only"

	if not args.dry_run and not ensure_mmdc_available():
		print("ERROR: 'mmdc' not found on PATH. Install with: npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
		return 2

	total_blocks = 0
	total_files = 0
	for md in iter_markdown_files(in_path, args.recursive):
		b, _ = process_file(md, out_dir, images_dir_rel, args.format, op_mode, args.dry_run, args.backup, args.force)
		if b:
			total_files += 1
			total_blocks += b

	print(f"Done. Files updated: {total_files}, diagrams processed: {total_blocks}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))


def _create_backup(md_file: Path) -> None:
	"""Create timestamped backup of Markdown file."""
	ts = datetime.now().strftime("%Y%m%d-%H%M%S")
	bak = md_file.with_suffix(md_file.suffix + f".bak-{ts}")
	try:
		shutil.copy2(md_file, bak)
		print(f"[BAK] {bak}")
	except (OSError, shutil.Error) as e:
		print(f"[BAK] failed for {md_file}: {e}", file=sys.stderr)
