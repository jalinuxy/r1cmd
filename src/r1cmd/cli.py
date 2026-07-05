"""User-friendly command-line interface for Arvan Storage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from r1cmd.constants import APP_NAME
from r1cmd.core import ArvanStorage, ArvanStorageError
from r1cmd.tui import run_interactive, run_setup

console = Console(stderr=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Arvan Storage — upload and manage your cloud files easily.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            f"  {APP_NAME}                 Open the interactive menu\n"
            f"  {APP_NAME} setup           Save your Access Key and Secret Key\n"
            f"  {APP_NAME} upload photo.jpg\n"
            f"  {APP_NAME} download reports/2024.pdf\n"
            f"  {APP_NAME} browse\n"
            f"  {APP_NAME} link photos/pic.jpg\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "setup",
        help="Save your Access Key and Secret Key (one-time setup)",
    )

    upload_parser = subparsers.add_parser("upload", help="Upload a file from your computer")
    upload_parser.add_argument("local_path", help="File on your computer")
    upload_parser.add_argument(
        "remote_path",
        nargs="?",
        default=None,
        help="Where to save it in storage (default: same file name)",
    )
    upload_parser.add_argument(
        "--space",
        metavar="NAME",
        help="Storage space to use (default: your saved space)",
    )

    download_parser = subparsers.add_parser("download", help="Download a file to your computer")
    download_parser.add_argument("remote_path", help="File path in your storage")
    download_parser.add_argument(
        "local_path",
        nargs="?",
        default=None,
        help="Where to save it locally (default: current folder)",
    )
    download_parser.add_argument("--space", metavar="NAME", help="Storage space to use")

    browse_parser = subparsers.add_parser("browse", help="List files in your storage")
    browse_parser.add_argument(
        "folder",
        nargs="?",
        default="",
        help="Folder to open (optional)",
    )
    browse_parser.add_argument("--space", metavar="NAME", help="Storage space to use")

    delete_parser = subparsers.add_parser("delete", help="Delete a file from your storage")
    delete_parser.add_argument("remote_path", help="File path in your storage")
    delete_parser.add_argument("--space", metavar="NAME", help="Storage space to use")

    link_parser = subparsers.add_parser("link", help="Create a temporary download link")
    link_parser.add_argument("remote_path", help="File path in your storage")
    link_parser.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="How long the link stays valid (default: 24)",
    )
    link_parser.add_argument("--space", metavar="NAME", help="Storage space to use")

    subparsers.add_parser("spaces", help="List your storage spaces")

    return parser


def _connect(space: Optional[str] = None) -> ArvanStorage:
    return ArvanStorage.connect(space=space)


def _human_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _cmd_upload(client: ArvanStorage, args: argparse.Namespace) -> int:
    client.upload(args.local_path, args.remote_path, space=args.space)
    remote = args.remote_path or Path(args.local_path).name
    space = args.space or client.default_space
    print(f"Uploaded to {space}/{remote}")
    return 0


def _cmd_download(client: ArvanStorage, args: argparse.Namespace) -> int:
    saved = client.download(args.remote_path, args.local_path, space=args.space)
    print(f"Saved to {saved}")
    return 0


def _cmd_browse(client: ArvanStorage, args: argparse.Namespace) -> int:
    space = args.space or client.default_space
    folders = client.list_folders(folder=args.folder, space=args.space)
    files = client.browse(folder=args.folder, space=args.space)

    if not folders and not files:
        location = f"{space}/{args.folder}" if args.folder else space
        print(f"No files in {location}")
        return 0

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    table.add_column("Modified", justify="right")

    for name in folders:
        table.add_row(f"{name}/", "—", "—")

    for item in files:
        table.add_row(
            item.name,
            _human_size(item.size),
            item.modified.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
    return 0


def _cmd_delete(client: ArvanStorage, args: argparse.Namespace) -> int:
    client.remove(args.remote_path, space=args.space)
    print(f"Deleted {args.remote_path}")
    return 0


def _cmd_link(client: ArvanStorage, args: argparse.Namespace) -> int:
    url = client.share_link(
        args.remote_path,
        space=args.space,
        expires_in=max(args.hours, 1) * 3600,
    )
    print(url)
    return 0


def _cmd_spaces(client: ArvanStorage, args: argparse.Namespace) -> int:
    spaces = client.list_spaces()
    if not spaces:
        print("No storage spaces found.")
        return 0

    current = client.default_space
    for name in spaces:
        marker = " (default)" if name == current else ""
        print(f"{name}{marker}")
    return 0


def _dispatch(client: ArvanStorage, args: argparse.Namespace) -> int:
    handlers = {
        "upload": _cmd_upload,
        "download": _cmd_download,
        "browse": _cmd_browse,
        "delete": _cmd_delete,
        "link": _cmd_link,
        "spaces": _cmd_spaces,
    }
    return handlers[args.command](client, args)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. No arguments opens the interactive menu."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            return run_interactive()
        if args.command == "setup":
            return run_setup()

        client = _connect(
            space=getattr(args, "space", None),
        )
        return _dispatch(client, args)
    except ArvanStorageError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("Interrupted.")
        return 130
    except FileNotFoundError as exc:
        target = getattr(exc, "filename", None) or exc
        console.print(f"[red]Error:[/red] file not found: {target}")
        return 1
    except OSError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
