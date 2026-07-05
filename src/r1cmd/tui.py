"""Interactive terminal UI for Arvan Storage."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from r1cmd.config import UserConfig
from r1cmd.constants import APP_NAME
from r1cmd.core import ArvanStorage, ArvanStorageError, RemoteFile

console = Console()

MENU_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold"),
    ("answer", "fg:cyan bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:green"),
])


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


def _format_time(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _banner() -> None:
    console.print(
        Panel(
            "[bold cyan]Arvan Storage[/bold cyan]\n"
            "Upload, download, and manage your cloud files — no technical setup required.",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def _require_tty() -> bool:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        console.print(
            "[yellow]Interactive mode needs a terminal.[/yellow]\n"
            f"Run [bold]{APP_NAME} setup[/bold] first, then use commands like "
            f"[bold]{APP_NAME} upload photo.jpg[/bold]."
        )
        return False
    return True


def _with_progress(description: str, action: Callable[[], object]) -> object:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description=description, total=None)
        return action()


def _pick_space(client: ArvanStorage, prompt: str) -> Optional[str]:
    spaces = client.list_spaces()
    if not spaces:
        console.print("[red]No storage spaces found on your account.[/red]")
        console.print("Create one in the Arvan panel, then try again.")
        return None

    current = client.default_space
    choices = []
    for name in spaces:
        label = name
        if name == current:
            label = f"{name}  (current)"
        choices.append(label)

    picked = questionary.select(prompt, choices=choices, style=MENU_STYLE).ask()
    if picked is None:
        return None
    return picked.split("  (current)")[0].strip()


def _pick_remote_file(client: ArvanStorage, folder: str = "") -> Optional[str]:
    files = client.browse(folder=folder)
    if not files:
        location = folder or "root"
        console.print(f"[yellow]No files found in '{location}'.[/yellow]")
        return None

    choices = [
        questionary.Choice(
            title=f"{item.name}  ({_human_size(item.size)})",
            value=item.path,
        )
        for item in files
    ]
    choices.append(questionary.Choice(title="« Back", value=""))
    picked = questionary.select("Choose a file:", choices=choices, style=MENU_STYLE).ask()
    if not picked:
        return None
    return picked


def run_setup(*, force: bool = False) -> int:
    """First-time setup: save access key, secret key, and default storage space."""
    if not _require_tty():
        return 1

    if UserConfig.exists() and not force:
        replace = questionary.confirm(
            "You already have saved credentials. Replace them?",
            default=False,
            style=MENU_STYLE,
        ).ask()
        if not replace:
            return 0

    _banner()
    console.print(
        "[dim]Get your Access Key and Secret Key from the Arvan Cloud panel "
        "(Object Storage → Access Keys).[/dim]\n"
    )

    access_key = questionary.text("Access Key:", style=MENU_STYLE).ask()
    if not access_key:
        return 1

    secret_key = questionary.password("Secret Key:", style=MENU_STYLE).ask()
    if not secret_key:
        return 1

    try:
        client = ArvanStorage.from_credentials(access_key, secret_key)
        spaces = _with_progress("Connecting to Arvan Storage...", client.list_spaces)
    except ArvanStorageError as exc:
        console.print(f"[red]Could not connect:[/red] {exc}")
        return 1

    if not spaces:
        console.print(
            "[yellow]Connected, but no storage spaces were found.[/yellow]\n"
            f"Create a space in the Arvan panel, then run [bold]{APP_NAME} setup[/bold] again."
        )
        UserConfig(access_key=access_key, secret_key=secret_key).save()
        return 0

    default_space = questionary.select(
        "Choose your default storage space:",
        choices=spaces,
        style=MENU_STYLE,
    ).ask()
    if default_space is None:
        return 1

    path = UserConfig(
        access_key=access_key,
        secret_key=secret_key,
        default_space=default_space,
    ).save()

    console.print(f"\n[green]✓[/green] Saved to [bold]{path}[/bold]")
    console.print(f"[green]✓[/green] Default space: [bold]{default_space}[/bold]")
    console.print(f"\nRun [bold]{APP_NAME}[/bold] to open the menu.")
    return 0


def _connect_or_setup() -> Optional[ArvanStorage]:
    if not UserConfig.exists():
        console.print("[yellow]First-time setup[/yellow] — let's connect your account.\n")
        if run_setup() != 0:
            return None

    try:
        return ArvanStorage.connect()
    except ArvanStorageError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return None


def _show_files(client: ArvanStorage, folder: str = "") -> None:
    files = client.browse(folder=folder)
    folders = client.list_folders(folder=folder)

    title = f"Files in '{client.default_space}'"
    if folder:
        title += f" / {folder}"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Size", justify="right")
    table.add_column("Modified", justify="right")

    for name in folders:
        table.add_row(f"📁 {name}", "—", "—")

    for item in files:
        table.add_row(item.name, _human_size(item.size), _format_time(item.modified))

    if not folders and not files:
        console.print(f"[yellow]This folder is empty.[/yellow]")
        return

    console.print(table)


def _action_upload(client: ArvanStorage) -> None:
    local_path = questionary.path("Path to the file on your computer:", style=MENU_STYLE).ask()
    if not local_path:
        return

    path = Path(local_path).expanduser()
    if not path.is_file():
        console.print(f"[red]File not found:[/red] {path}")
        return

    remote_name = questionary.text(
        "Save as (in your storage):",
        default=path.name,
        style=MENU_STYLE,
    ).ask()
    if not remote_name:
        return

    folder = questionary.text(
        "Folder (optional, press Enter to skip):",
        default="",
        style=MENU_STYLE,
    ).ask()
    if folder is None:
        return

    remote_path = f"{folder.rstrip('/')}/{remote_name}" if folder.strip() else remote_name

    try:
        _with_progress("Uploading...", lambda: client.upload(path, remote_path))
        console.print(f"[green]✓[/green] Uploaded to [bold]{remote_path}[/bold]")
    except ArvanStorageError as exc:
        console.print(f"[red]Upload failed:[/red] {exc}")


def _action_download(client: ArvanStorage) -> None:
    folder = questionary.text(
        "Folder to browse (optional):",
        default="",
        style=MENU_STYLE,
    ).ask()
    if folder is None:
        return

    remote_path = _pick_remote_file(client, folder=folder)
    if not remote_path:
        return

    default_local = Path(remote_path).name
    local_path = questionary.text(
        "Save to (on your computer):",
        default=str(Path.cwd() / default_local),
        style=MENU_STYLE,
    ).ask()
    if not local_path:
        return

    try:
        saved = _with_progress(
            "Downloading...",
            lambda: client.download(remote_path, local_path),
        )
        console.print(f"[green]✓[/green] Saved to [bold]{saved}[/bold]")
    except ArvanStorageError as exc:
        console.print(f"[red]Download failed:[/red] {exc}")


def _action_browse(client: ArvanStorage) -> None:
    folder = questionary.text(
        "Folder to open (optional):",
        default="",
        style=MENU_STYLE,
    ).ask()
    if folder is None:
        return
    _show_files(client, folder=folder)


def _action_delete(client: ArvanStorage) -> None:
    folder = questionary.text(
        "Folder to browse (optional):",
        default="",
        style=MENU_STYLE,
    ).ask()
    if folder is None:
        return

    remote_path = _pick_remote_file(client, folder=folder)
    if not remote_path:
        return

    confirm = questionary.confirm(
        f"Delete '{remote_path}' permanently?",
        default=False,
        style=MENU_STYLE,
    ).ask()
    if not confirm:
        return

    try:
        _with_progress("Deleting...", lambda: client.remove(remote_path))
        console.print(f"[green]✓[/green] Deleted [bold]{remote_path}[/bold]")
    except ArvanStorageError as exc:
        console.print(f"[red]Delete failed:[/red] {exc}")


def _action_share(client: ArvanStorage) -> None:
    folder = questionary.text(
        "Folder to browse (optional):",
        default="",
        style=MENU_STYLE,
    ).ask()
    if folder is None:
        return

    remote_path = _pick_remote_file(client, folder=folder)
    if not remote_path:
        return

    hours = questionary.select(
        "Link valid for:",
        choices=["1 hour", "6 hours", "24 hours", "7 days"],
        style=MENU_STYLE,
    ).ask()
    if hours is None:
        return

    expiry = {"1 hour": 3600, "6 hours": 21600, "24 hours": 86400, "7 days": 604800}[hours]

    try:
        url = _with_progress(
            "Creating link...",
            lambda: client.share_link(remote_path, expires_in=expiry),
        )
        console.print("\n[green]✓[/green] Temporary download link:\n")
        console.print(url)
        console.print(f"\n[dim]Expires in {hours.lower()}.[/dim]")
    except ArvanStorageError as exc:
        console.print(f"[red]Could not create link:[/red] {exc}")


def _action_switch_space(client: ArvanStorage) -> ArvanStorage:
    picked = _pick_space(client, "Switch to which storage space?")
    if not picked:
        return client

    config = UserConfig.load()
    config.default_space = picked
    config.save()
    console.print(f"[green]✓[/green] Now using [bold]{picked}[/bold]")
    return ArvanStorage.connect()


def _action_settings() -> None:
    choice = questionary.select(
        "Settings",
        choices=[
            "Update credentials",
            "Forget saved credentials",
            "« Back",
        ],
        style=MENU_STYLE,
    ).ask()

    if choice == "Update credentials":
        run_setup(force=True)
    elif choice == "Forget saved credentials":
        confirm = questionary.confirm(
            "Remove saved Access Key and Secret Key from this computer?",
            default=False,
            style=MENU_STYLE,
        ).ask()
        if confirm:
            UserConfig.load().clear()
            console.print("[green]✓[/green] Credentials removed.")


def run_interactive() -> int:
    """Main interactive menu."""
    if not _require_tty():
        return 1

    client = _connect_or_setup()
    if client is None:
        return 1

    _banner()
    console.print(
        f"Connected · space: [bold cyan]{client.default_space}[/bold cyan]\n"
    )

    while True:
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Upload a file",
                "Download a file",
                "Browse my files",
                "Delete a file",
                "Get a shareable link",
                "Switch storage space",
                "Settings",
                "Exit",
            ],
            style=MENU_STYLE,
        ).ask()

        if choice is None or choice == "Exit":
            console.print("\n[dim]Goodbye![/dim]")
            return 0

        try:
            if choice == "Upload a file":
                _action_upload(client)
            elif choice == "Download a file":
                _action_download(client)
            elif choice == "Browse my files":
                _action_browse(client)
            elif choice == "Delete a file":
                _action_delete(client)
            elif choice == "Get a shareable link":
                _action_share(client)
            elif choice == "Switch storage space":
                client = _action_switch_space(client)
            elif choice == "Settings":
                _action_settings()
        except ArvanStorageError as exc:
            console.print(f"[red]Error:[/red] {exc}")

        console.print()
