from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QMenu,
    QToolBar,
    QAbstractItemView,
    QStyle,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
import os
import posixpath
import sys
import subprocess
import stat as statmod
import datetime
import tempfile
import webbrowser


class QActionButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { padding: 4px 8px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #E5E7EB; }"
        )


class ServerFilesView(QWidget):
    """Remote files panel with MobaXterm-like context menu."""
    def __init__(self, ssh_client=None):
        super().__init__()
        self.ssh_client = ssh_client
        self.sftp = None
        self.current_path = "."
        self._build_ui()

    # ---- UI ----
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # header: path + toolbar
        header_row = QHBoxLayout()
        self.path_label = QLabel(self.current_path)
        self.path_label.setStyleSheet("font-weight: 500;")
        header_row.addWidget(self.path_label)
        header_row.addStretch(1)

        toolbar = QToolBar()
        toolbar.setIconSize(toolbar.iconSize())
        self.btn_up = QActionButton("Up")
        self.btn_refresh = QActionButton("Refresh")
        self.btn_download = QActionButton("Download")
        self.btn_upload = QActionButton("Upload")
        self.btn_new_folder = QActionButton("New Folder")
        self.btn_delete = QActionButton("Delete")

        header_row.addWidget(self.btn_up)
        header_row.addWidget(self.btn_refresh)
        header_row.addWidget(self.btn_download)
        header_row.addWidget(self.btn_upload)
        header_row.addWidget(self.btn_new_folder)
        header_row.addWidget(self.btn_delete)

        layout.addLayout(header_row)

        # tree
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Name", "Size", "Type", "Modified"])
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.tree)

        # connections
        self.btn_up.clicked.connect(self.go_up)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_download.clicked.connect(self.action_download)
        self.btn_upload.clicked.connect(self.action_upload)
        self.btn_new_folder.clicked.connect(self.action_new_folder)
        self.btn_delete.clicked.connect(self.action_delete)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

    # ---- SFTP helpers ----
    
    def _ensure_sftp(self):
        """Ensure we have an SFTP client and a sane absolute current_path.

        We normalize "." to the server's real working directory so that
        later calls like ``get()`` use absolute paths (avoids ``No such file``).
        """
        if not self.ssh_client or not getattr(self.ssh_client, "client", None):
            return None
        if self.sftp is None:
            try:
                self.sftp = self.ssh_client.client.open_sftp()
            except Exception:
                self.sftp = None
        if self.sftp is not None and self.current_path in (".", ""):
            try:
                self.current_path = self.sftp.normalize(".")
            except Exception:
                # if normalize fails, keep whatever we had
                pass
        return self.sftp

# ---- Loading ----
    def load_root(self, path=None):
        if path:
            self.current_path = path
        if not self._ensure_sftp():
            self.tree.clear()
            self.path_label.setText("Not connected")
            return

        self.tree.clear()
        self.path_label.setText(self.current_path)

        try:
            entries = self.sftp.listdir_attr(self.current_path)
        except Exception:
            self.tree.clear()
            self.path_label.setText(f"{self.current_path} (unreachable)")
            return

        # standard icons
        style = self.style()
        dir_icon = style.standardIcon(QStyle.SP_DirIcon)
        file_icon = style.standardIcon(QStyle.SP_FileIcon)

        # Add '..' entry
        up_item = QTreeWidgetItem(["..", "", "Parent", ""])
        up_item.setIcon(0, dir_icon)
        self.tree.addTopLevelItem(up_item)

        # Sort: directories first, then files
        def sort_key(attr):
            is_dir = statmod.S_ISDIR(attr.st_mode)
            return (0 if is_dir else 1, attr.filename.lower())

        for attr in sorted(entries, key=sort_key):
            name = attr.filename
            mode = attr.st_mode
            is_dir = statmod.S_ISDIR(mode)
            size = "-" if is_dir else str(attr.st_size)

            if is_dir:
                kind = "Folder"
            else:
                ext = os.path.splitext(name)[1].lower()
                if ext == ".py":
                    kind = "Python file"
                elif ext in (".sh", ".bash"):
                    kind = "Shell script"
                elif ext in (".txt", ".log"):
                    kind = "Text file"
                elif ext in (".ipynb",):
                    kind = "Notebook"
                else:
                    kind = f"{ext} file" if ext else "File"

            mtime = datetime.datetime.fromtimestamp(attr.st_mtime).strftime("%Y-%m-%d %H:%M")
            item = QTreeWidgetItem([name, size, kind, mtime])
            item.setData(0, Qt.UserRole, mode)
            if is_dir:
                item.setIcon(0, dir_icon)
            else:
                item.setIcon(0, file_icon)
            self.tree.addTopLevelItem(item)

        self.tree.resizeColumnToContents(0)

    def refresh(self):
        """Reload current directory"""
        self.load_root(self.current_path)


    def go_up(self):
        # Navigate to parent directory
        if self.current_path in ("/", ""):
            parent = "/"
        else:
            parent = os.path.dirname(self.current_path.rstrip("/")) or "/"
        self.current_path = parent
        self.load_root(self.current_path)

    # ---- Item helpers ----
    def _selected_items(self):
        return self.tree.selectedItems() or []

    def _selected_item(self):
        items = self.tree.selectedItems()
        return items[0] if items else None

    def _item_path_mode(self, item):
        name = item.text(0)
        if name == "..":
            return None, None
        mode = item.data(0, Qt.UserRole)
        path = posixpath.join(self.current_path, name) if self.current_path != "/" else "/" + name
        return path, mode

    # ---- Toolbar actions ----
    def action_download(self):
        # allow multi-select download (files only)
        items = [
            it for it in self._selected_items()
            if self._item_path_mode(it)[0]
            and not statmod.S_ISDIR(self._item_path_mode(it)[1])
        ]
        if not items:
            return
        dest_dir = QFileDialog.getExistingDirectory(self, "Download to")
        if not dest_dir:
            return
        self._ensure_sftp()
        for it in items:
            path, mode = self._item_path_mode(it)
            local_path = os.path.join(dest_dir, os.path.basename(path))
            try:
                self.sftp.get(path, local_path)
            except Exception as e:
                print("Download error:", e)

    def action_upload(self):
        if not self._ensure_sftp():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload file")
        if not file_path:
            return
        remote_path = posixpath.join(self.current_path, os.path.basename(file_path))
        try:
            self.sftp.put(file_path, remote_path)
            self.refresh()
        except Exception as e:
            print("Upload error:", e)

    def action_new_folder(self):
        if not self._ensure_sftp():
            return
        name, ok = QFileDialog.getSaveFileName(self, "New folder name", posixpath.join(self.current_path, "new_folder"))
        if not ok or not name:
            return
        # QFileDialog returns full path; we only need folder name or path
        remote_path = name
        try:
            self.sftp.mkdir(remote_path)
            self.refresh()
        except Exception as e:
            print("mkdir error:", e)

    def action_delete(self):
        items = self._selected_items()
        if not items:
            return
        self._ensure_sftp()
        for it in items:
            path, mode = self._item_path_mode(it)
            if not path:
                continue
            try:
                if statmod.S_ISDIR(mode):
                    self.sftp.rmdir(path)
                else:
                    self.sftp.remove(path)
            except Exception as e:
                print("Delete error:", e)
        self.refresh()

    # ---- Context menu ----
    def show_context_menu(self, pos: QPoint):
        item = self._selected_item()
        menu = QMenu(self)
        if item:
            path, mode = self._item_path_mode(item)
        else:
            path, mode = None, None

        # Mirror MobaXterm-style actions
        act_open = menu.addAction("Open")
        act_open_text = menu.addAction("Open with default text editor")
        act_open_prog = menu.addAction("Open with default program...")
        act_compare = menu.addAction("Compare file with...")
        menu.addSeparator()
        act_download = menu.addAction("Download")
        act_delete = menu.addAction("Delete")
        act_rename = menu.addAction("Rename")
        menu.addSeparator()
        act_copy_path = menu.addAction("Copy file path")
        act_copy_to_term = menu.addAction("Copy file path to terminal")
        menu.addSeparator()
        act_props = menu.addAction("Properties")
        act_perm = menu.addAction("Permissions")

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_open or chosen == act_open_text or chosen == act_open_prog:
            if path and mode and not statmod.S_ISDIR(mode):
                self._open_local(path)
        elif chosen == act_download:
            self.action_download()
        elif chosen == act_delete:
            self.action_delete()
        elif chosen == act_rename:
            self._rename(path)
        elif chosen == act_copy_path:
            if path:
                QGuiApplication.clipboard().setText(path)
        elif chosen == act_copy_to_term:
            if path:
                # For now: also copy to clipboard; user can paste into terminal
                QGuiApplication.clipboard().setText(path)
        elif chosen == act_props:
            self._show_properties(path, mode)
        elif chosen == act_perm:
            self._show_permissions(path, mode)

    # ---- Double click ----
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        path, mode = self._item_path_mode(item)
        if item.text(0) == "..":
            self.go_up()
            return
        if not path or mode is None:
            return
        if statmod.S_ISDIR(mode):
            self.current_path = path
            self.load_root(self.current_path)
        else:
            self._open_local(path)

    # ---- Helper methods ----
    
    def _open_local(self, remote_path: str):
        """Download a remote file to a local cache.

        On Windows we try to open it with the system default program.
        On Linux/macOS we *only* download and print the local path,
        不再调用 xdg-open，避免在没有 GUI 的服务器上各种报错。
        """
        if not self._ensure_sftp():
            return
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".bioflow_cache")
            os.makedirs(cache_dir, exist_ok=True)
            local_name = os.path.basename(remote_path)
            tmp_path = os.path.join(cache_dir, local_name)
            self.sftp.get(remote_path, tmp_path)
            # Windows 下用系统默认程序打开，其它平台只打印路径
            if sys.platform.startswith("win"):
                try:
                    os.startfile(tmp_path)  # type: ignore[attr-defined]
                except Exception as e:
                    print("open_local error:", e)
            else:
                print(f"Downloaded to: {tmp_path}")
        except Exception as e:
            print("open_local error:", e)
    def _rename(self, remote_path: str | None):
        if not remote_path or not self._ensure_sftp():
            return
        dir_name = os.path.dirname(remote_path)
        base_name = os.path.basename(remote_path)
        new_path, ok = QFileDialog.getSaveFileName(self, "Rename to", os.path.join(dir_name, base_name))
        if not ok or not new_path:
            return
        try:
            self.sftp.rename(remote_path, new_path)
            self.refresh()
        except Exception as e:
            print("rename error:", e)

    def _show_properties(self, remote_path: str | None, mode):
        if not remote_path or not self._ensure_sftp():
            return
        try:
            st = self.sftp.stat(remote_path)
        except Exception as e:
            print("stat error:", e)
            return
        size = st.st_size
        mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        kind = "Directory" if statmod.S_ISDIR(mode or st.st_mode) else "File"
        print(f"Properties for {remote_path}: type={kind}, size={size}, mtime={mtime}")

    def _show_permissions(self, remote_path: str | None, mode):
        if not remote_path or not self._ensure_sftp():
            return
        try:
            st = self.sftp.stat(remote_path)
        except Exception as e:
            print("perm error:", e)
            return
        perms = oct(st.st_mode & 0o777)
        print(f"Permissions for {remote_path}: {perms}")
