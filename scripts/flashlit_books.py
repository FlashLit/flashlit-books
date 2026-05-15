#!/usr/bin/env python3
"""List Flashlit books for the authenticated user."""

from __future__ import annotations

import argparse
import json
import sys

from flashlit_client import FlashlitError, get_chapter_metadata, get_chapters_text, list_books


def print_table(result: dict, show_ids: bool = False) -> None:
    data = result.get("data", [])
    meta = result.get("metadata", {})

    total = meta.get("total_count", "unknown")
    page_size = meta.get("page_size", len(data))
    current_page = meta.get("current_page")
    if current_page is not None:
        print(f"Total: {total} | Page: {current_page} | Page size: {page_size}")
    else:
        print(f"Total: {total} | Page size: {page_size}")
    print()

    if not data:
        print("No books found.")
        return

    for i, book in enumerate(data, 1):
        title = book.get("title") or "Untitled"
        author = book.get("author") or "Unknown Author"
        status = book.get("processing_status") or "unknown"
        activated = book.get("isFlashlitActivated")
        language = book.get("language") or ""
        print(f"{i}. {title} — {author}")
        print(f"   status={status}, activated={activated}, language={language}")
        if show_ids:
            print(f"   id={book.get('_id') or book.get('md5_value')}")
            if book.get("epub_url"):
                print(f"   epub={book.get('epub_url')}")
        print()


def cmd_list(args: argparse.Namespace) -> int:
    result = list_books(
        skip=args.skip,
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        show_imported=not args.not_imported,
        search=args.search,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_table(result, show_ids=args.ids)
    return 0


def cmd_chapter_metadata(args: argparse.Namespace) -> int:
    result = get_chapter_metadata(args.book_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_chapters_text(args: argparse.Namespace) -> int:
    result = get_chapters_text(args.book_id, args.indices)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    chapter_texts = result.get("chapter_texts", {})
    missing = result.get("missing_chapters", [])
    for index in args.indices:
        text = chapter_texts.get(str(index)) or chapter_texts.get(index)
        if text is None:
            print(f"--- Chapter {index}: missing ---")
            continue
        if args.first_paragraph:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            text = paragraphs[0] if paragraphs else ""
        elif args.max_chars and len(text) > args.max_chars:
            text = text[: args.max_chars].rstrip() + "…"
        print(f"--- Chapter {index} ---")
        print(text)
        print()
    if missing:
        print(f"Missing chapters: {missing}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="List Flashlit books")
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List authenticated user's Flashlit books")
    list_parser.add_argument("--skip", type=int, default=0, help="Number of books to skip")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of books to return")
    list_parser.add_argument("--sort-by", default="created_at", help="Field to sort by")
    list_parser.add_argument("--sort-order", type=int, choices=[-1, 1], default=-1, help="-1 descending, 1 ascending")
    list_parser.add_argument("--search", help="Search title or author")
    list_parser.add_argument("--not-imported", action="store_true", help="Show non-imported/non-activated books")
    list_parser.add_argument("--ids", action="store_true", help="Show book IDs and EPUB URLs")
    list_parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    list_parser.set_defaults(func=cmd_list)

    metadata_parser = sub.add_parser("chapter-metadata", help="Fetch processed chapter metadata for a book")
    metadata_parser.add_argument("book_id", help="Book md5_value / ID")
    metadata_parser.set_defaults(func=cmd_chapter_metadata)

    text_parser = sub.add_parser("chapters-text", help="Fetch raw combined text for one or more chapter indices")
    text_parser.add_argument("book_id", help="Book md5_value / ID")
    text_parser.add_argument("indices", nargs="+", type=int, help="Chapter indices to fetch")
    text_parser.add_argument("--first-paragraph", action="store_true", help="Print only the first non-empty paragraph per chapter")
    text_parser.add_argument("--max-chars", type=int, default=0, help="Truncate each chapter to this many characters")
    text_parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    text_parser.set_defaults(func=cmd_chapters_text)

    # Default to `list` if no subcommand is provided.
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["list", *argv]

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FlashlitError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
