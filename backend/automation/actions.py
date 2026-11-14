import os
import platform
import re
import shutil
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import os


APP_COMMANDS = {
    "vscode": "code",
    "firefox": "firefox",
    "files": "nautilus",
}
FOLDER_PATHS = {
    "home": Path.home(),
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "desktop": Path.home() / "Desktop",
}
SEARCH_PATHS = tuple(
    path for path in (FOLDER_PATHS["downloads"], FOLDER_PATHS["documents"], FOLDER_PATHS["desktop"])
    if path.exists()
)


def preview_action(command: str):
    text = command.strip()
    lowered = text.lower()

    if re.search(r"\b(time|date)\b", lowered) and re.search(r"\b(what|current|tell me|show)\b", lowered):
        return {"kind": "time", "display": "Show the current local date and time.", "requires_confirmation": False}
    if re.search(r"\b(system information|system info|computer information)\b", lowered):
        return {"kind": "system_info", "display": "Show basic operating system information.", "requires_confirmation": False}

    app_match = re.fullmatch(r"(?:please\s+)?(?:open|launch|start)\s+(?:my\s+)?(visual studio code|vs code|vscode|firefox|files|file manager)", lowered)
    if app_match:
        alias = app_match.group(1)
        app = "vscode" if alias in {"visual studio code", "vs code", "vscode"} else "firefox" if alias == "firefox" else "files"
        return {
            "kind": "open_app",
            "app": app,
            "display": f"Launch the allowlisted {app} application.",
            "requires_confirmation": True,
        }

    folder_match = re.fullmatch(r"(?:please\s+)?open\s+(?:my\s+)?(home|downloads|documents|desktop)(?:\s+folder)?", lowered)
    if folder_match:
        folder = folder_match.group(1)
        return {
            "kind": "open_folder",
            "folder": folder,
            "display": f"Open your {folder} folder.",
            "requires_confirmation": True,
        }

    search_match = re.fullmatch(r"(?:find|search for)\s+files?\s+(?:named\s+)?(.{1,100})", text, re.IGNORECASE)
    if search_match:
        query = search_match.group(1).strip()
        return {
            "kind": "search_files",
            "query": query,
            "display": f"Search filenames in Downloads, Documents, and Desktop for '{query}'.",
            "requires_confirmation": True,
        }

    info_match = re.fullmatch(r"(?:file info|show file info for)\s+([^/\\]{1,160})", text, re.IGNORECASE)
    if info_match:
        filename = info_match.group(1).strip()
        if not filename or filename in {".", ".."}:
            raise ValueError("Enter a filename, not a path.")
        return {
            "kind": "file_info",
            "filename": filename,
            "display": f"Read metadata for the matching file named '{filename}' in approved folders. File contents will not be opened.",
            "requires_confirmation": True,
        }

    organize_match = re.fullmatch(r"organize file\s+([^/\\]{1,160})", text, re.IGNORECASE)
    if organize_match:
        filename = organize_match.group(1).strip()
        source = _find_download_file(filename)
        if source is None:
            raise ValueError("That filename was not found in Downloads.")
        extension = source.suffix.lower().lstrip(".") or "other"
        destination = FOLDER_PATHS["downloads"] / "Organized" / extension
        return {
            "kind": "organize_file",
            "source": str(source),
            "destination": str(destination / source.name),
            "display": f"Move {source.name} into Downloads/Organized/{extension}/ without overwriting existing files.",
            "requires_confirmation": True,
        }

    website_match = re.fullmatch(r"(?:please\s+)?open\s+(https?://\S+|[\w.-]+\.[a-z]{2,}(?:/\S*)?)", text, re.IGNORECASE)
    if website_match:
        url = website_match.group(1)
        if not urlparse(url).scheme:
            url = f"https://{url}"
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only valid HTTP or HTTPS website addresses can be opened.")
        return {
            "kind": "open_website",
            "url": url,
            "display": f"Open {url} in the default browser.",
            "requires_confirmation": True,
        }

    raise ValueError("That action is not on the approved list.")


def execute_action(action):
    kind = action["kind"]
    if kind == "time":
        return {"result": datetime.now().astimezone().strftime("%A, %Y-%m-%d %H:%M:%S %Z")}
    if kind == "system_info":
        return {
            "result": f"{platform.system()} {platform.release()} ({platform.machine()}); Python {platform.python_version()}"
        }
    if kind == "open_app":
        executable = shutil.which(APP_COMMANDS[action["app"]])
        if not executable:
            raise RuntimeError(f"{action['app']} is not installed or is not on PATH.")
        subprocess.Popen([executable], start_new_session=True)
        return {"result": f"Launched {action['app']}."}
    if kind == "open_folder":
        path = FOLDER_PATHS[action["folder"]]
        opener = shutil.which("xdg-open")
        if not path.exists() or not opener:
            raise RuntimeError("The selected folder or xdg-open is unavailable.")
        subprocess.Popen([opener, str(path)], start_new_session=True)
        return {"result": f"Opened {path}."}
    if kind == "open_website":
        if not webbrowser.open(action["url"]):
            raise RuntimeError("The default browser could not open that address.")
        return {"result": f"Opened {action['url']}."}
    if kind == "search_files":
        query = action["query"].casefold()
        matches = []
        visited = 0
        for root in SEARCH_PATHS:
            for directory, subdirectories, filenames in os.walk(root):
                subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
                for filename in filenames:
                    visited += 1
                    if query in filename.casefold():
                        matches.append(str(Path(directory) / filename))
                        if len(matches) >= 10:
                            break
                    if visited >= 5000 or len(matches) >= 10:
                        break
                if visited >= 5000 or len(matches) >= 10:
                    break
            if visited >= 5000 or len(matches) >= 10:
                break
        return {"result": matches or ["No matching filenames found."], "searched_files": visited}
    if kind == "file_info":
        matches = []
        target = action["filename"].casefold()
        for root in SEARCH_PATHS:
            for directory, subdirectories, filenames in os.walk(root):
                subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
                for filename in filenames:
                    if filename.casefold() == target:
                        file_path = Path(directory) / filename
                        details = file_path.stat()
                        matches.append({
                            "path": str(file_path),
                            "size_bytes": details.st_size,
                            "modified_at": datetime.fromtimestamp(details.st_mtime).astimezone().isoformat(),
                        })
                        if len(matches) >= 10:
                            break
                if len(matches) >= 10:
                    break
        return {"result": matches or ["No matching file found."], "contents_read": False}
    if kind == "organize_file":
        source = Path(action["source"]).resolve()
        downloads_root = FOLDER_PATHS["downloads"].resolve()
        if not source.is_file() or downloads_root not in source.parents:
            raise RuntimeError("The selected file is no longer in Downloads.")
        destination = Path(action["destination"]).resolve()
        if destination.exists():
            raise RuntimeError("A file with that name already exists in the destination.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return {"result": f"Moved {source.name} to {destination}."}
    raise ValueError("That action is not on the approved list.")


def _find_download_file(filename):
    root = FOLDER_PATHS["downloads"]
    if not root.exists():
        return None
    target = filename.casefold()
    visited = 0
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
        for name in filenames:
            visited += 1
            if name.casefold() == target:
                return (Path(directory) / name).resolve()
            if visited >= 5000:
                return None
    return None