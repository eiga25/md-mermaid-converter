#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "MD Mermaid Converter"
DEFAULT_PROFILES_PATH = Path(__file__).with_name("profiles.json")
DEFAULT_OUTPUT_SUFFIX = "_converted"

I18N_PATH = Path(__file__).with_name("i18n.json")
SETTINGS_PATH = Path(__file__).with_name("settings.json")


def load_profiles(path: Path) -> dict:
    """Load profiles from JSON file."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_profiles(path: Path, data: dict) -> None:
    """Save profiles to JSON file."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x640")
        self.resizable(True, True)

        # Load i18n from file
        self._i18n = self.load_i18n()

        # Defaults
        cwd = str(Path.cwd())
        self.input_value = cwd
        self.out_value = cwd + DEFAULT_OUTPUT_SUFFIX
        self.input_var = tk.StringVar(value=cwd)
        self.out_dir_var = tk.StringVar(value=self.out_value)

        # Options state
        self.path_mode_var = tk.StringVar(value="relative")
        self.path_display_var = tk.StringVar(value="")
        self.images_mode_var = tk.StringVar(value="per-file")
        self.recursive_var = tk.BooleanVar(value=False)
        self.format_var = tk.StringVar(value="png")
        self.mode_var = tk.StringVar(value="render-keep")
        self.clear_log_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)

        # Language and input selection (persist last choice)
        self.lang_var = tk.StringVar(value=self._load_last_lang())
        self.input_kind = "folder"  # 'folder' | 'files'
        self.input_files = []

        # Profile dirty tracking
        self._last_profile_name = None
        self._last_loaded_state = None

        self.profiles_path = DEFAULT_PROFILES_PATH
        self.profiles = load_profiles(self.profiles_path)

        # Build UI
        self._build_ui()
        self._refresh_profile_list()
        self._refresh_display()

        # Language change: persist + rebuild UI without clearing profiles
        self.lang_var.trace_add("write", lambda *_: self.on_lang_change())

    def _load_last_lang(self) -> str:
        """Load last used language from settings file."""
        try:
            if SETTINGS_PATH.exists():
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                lang = data.get("lang")
                if lang in ("zh", "en"):
                    return lang
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load language settings: {e}")
        return "zh"

    def _save_last_lang(self) -> None:
        """Save current language to settings file."""
        try:
            data = {"lang": self.lang_var.get()}
            SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, TypeError) as e:
            print(f"Warning: Failed to save language settings: {e}")

    def on_lang_change(self) -> None:
        """Handle language change by rebuilding UI."""
        self._save_last_lang()
        self._build_ui()
        self._refresh_profile_list()
        self._refresh_display()

    def load_i18n(self) -> dict:
        """Load i18n strings from file, with fallback."""
        try:
            if I18N_PATH.exists():
                return json.loads(I18N_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load i18n file: {e}")
        # Minimal fallback to avoid crashes if file missing
        return {
            "zh": {"profile": "配置", "save": "保存", "delete": "删除", "language": "语言", "render": "渲染", "dry_run": "试运行", "input_label": "输入 (文件/文件夹)", "browse": "浏览", "out_label": "输出目录", "format": "格式", "mode": "模式", "recursive": "递归", "path": "路径", "image_store": "图片存放", "per_file": "每文档 [name]_images (同目录)", "out_images": "单一 images (在输出目录)", "clear_log": "运行前清空日志", "backup": "修改前备份 .md", "risk_title": "风险提示", "risk_msg": "输出目录与输入目录相同，且未开启备份，将覆盖源 Markdown。是否继续？", "delete_confirm": "删除配置 '{name}'?", "select_input": "选择输入", "select_folder": "选择文件夹", "select_files": "选择文件(可多选)", "files_suffix": "个文件", "profile_changed": "当前设置已修改，是否加载所选配置并覆盖当前更改？" },
            "en": {"profile": "Profile", "save": "Save", "delete": "Delete", "language": "Language", "render": "Render", "dry_run": "Dry Run", "input_label": "Input (File/Folder)", "browse": "Browse", "out_label": "Output Dir", "format": "Format", "mode": "Mode", "recursive": "Recursive", "path": "Path", "image_store": "Image placement", "per_file": "Per file [name]_images (sibling)", "out_images": "Single images (under output)", "clear_log": "Clear log before run", "backup": "Backup .md before modify", "risk_title": "Risk Warning", "risk_msg": "Output equals input and backup is OFF. This will overwrite source Markdown. Continue?", "delete_confirm": "Delete profile '{name}'?", "select_input": "Select Input", "select_folder": "Select Folder", "select_files": "Select File(s)", "files_suffix": "files", "profile_changed": "Current settings changed. Load selected profile and discard changes?" }
        }

    def _build_ui(self) -> None:
        """Build or rebuild the main UI."""
        # Rebuildable root (for language switch)
        if hasattr(self, "_ui_root") and self._ui_root is not None:
            try:
                self._ui_root.destroy()
            except Exception:
                pass
        root = ttk.Frame(self, padding=12)
        self._ui_root = root
        root.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for c in range(0, 8):
            root.columnconfigure(c, weight=1 if c == 1 else 0)
        root.columnconfigure(4, minsize=24)
        root.rowconfigure(8, weight=1)

        def glabel(r, c, text):
            ttk.Label(root, text=text).grid(row=r, column=c, sticky="w", padx=4, pady=4)

        t = self.t

        # Preserve previous profile selection
        prev_profile = None
        if hasattr(self, "profile_var"):
            prev_profile = self.profile_var.get()

        # Profile row
        glabel(0, 0, t("profile") + ":")
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(root, textvariable=self.profile_var, state="readonly")
        self.profile_combo.grid(row=0, column=1, columnspan=3, sticky="we", padx=4)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)
        ttk.Button(root, text=t("save"), command=self.on_save_profile).grid(row=0, column=5, padx=2)
        ttk.Button(root, text=t("delete"), command=self.on_delete_profile).grid(row=0, column=6, padx=2)
        lang_combo = ttk.Combobox(root, width=8, state="readonly", values=["zh", "en"], textvariable=self.lang_var)
        lang_combo.grid(row=0, column=7, sticky="e")

        # Repopulate profile list and restore selection
        self._refresh_profile_list()
        if prev_profile and prev_profile in self.profiles:
            self.profile_var.set(prev_profile)

        ttk.Separator(root).grid(row=1, column=0, columnspan=8, sticky="we", pady=6)

        # Input row
        glabel(2, 0, t("input_label"))
        self.input_entry = ttk.Entry(root, textvariable=self.input_var)
        self.input_entry.grid(row=2, column=1, columnspan=5, sticky="we", padx=4)
        ttk.Button(root, text=t("select_folder"), command=lambda: self.on_browse_input_force("folder")).grid(row=2, column=6, sticky="e", padx=2)
        ttk.Button(root, text=t("select_files"), command=lambda: self.on_browse_input_force("files")).grid(row=2, column=7, sticky="e", padx=2)

        # Out dir row
        glabel(3, 0, t("out_label"))
        self.out_entry = ttk.Entry(root, textvariable=self.out_dir_var)
        self.out_entry.grid(row=3, column=1, columnspan=6, sticky="we", padx=4)
        ttk.Button(root, text=t("browse"), command=self.on_browse_outdir).grid(row=3, column=7, sticky="e", padx=(8, 4))

        # Row 4: Format | Mode
        row4 = ttk.Frame(root)
        row4.grid(row=4, column=0, columnspan=8, sticky="we", pady=(8, 4))
        
        # Format
        format_frame = ttk.Frame(row4)
        format_frame.pack(side=tk.LEFT, padx=(0, 24))
        ttk.Label(format_frame, text=t("format") + ":").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(format_frame, width=8, textvariable=self.format_var, values=["png", "svg"], state="readonly").pack(side=tk.LEFT)
        
        # Mode (with internationalized display values)
        mode_frame = ttk.Frame(row4)
        mode_frame.pack(side=tk.LEFT, padx=(0, 24))
        ttk.Label(mode_frame, text=t("mode") + ":").pack(side=tk.LEFT, padx=(0, 6))
        
        # Create mode mapping: display -> internal value
        self._mode_labels = {
            "export": (t("mode_export"), "export"),
            "render": (t("mode_render"), "render"),
            "render-keep": (t("mode_render_keep"), "render-keep")
        }
        mode_display_values = [self._mode_labels["export"][0], self._mode_labels["render"][0], self._mode_labels["render-keep"][0]]
        
        # Get current display label
        current_mode = self.mode_var.get()
        current_mode_label = self._mode_labels.get(current_mode, self._mode_labels["render-keep"])[0]
        self.mode_display_var = tk.StringVar(value=current_mode_label)
        
        mode_combo = ttk.Combobox(mode_frame, width=14, textvariable=self.mode_display_var, values=mode_display_values, state="readonly")
        mode_combo.pack(side=tk.LEFT)
        
        def on_mode_display_change(*_):
            display_lbl = self.mode_display_var.get()
            # Find internal value from display label
            for internal_val, (display_val, _) in self._mode_labels.items():
                if display_lbl == display_val:
                    if internal_val != self.mode_var.get():
                        self.mode_var.set(internal_val)
                    break
        self.mode_display_var.trace_add("write", on_mode_display_change)
        
        # Recursive checkbox
        ttk.Checkbutton(row4, text=t("recursive"), variable=self.recursive_var).pack(side=tk.LEFT, padx=(0, 16))
        
        # Row 5: Image placement (radio buttons span the row)
        row5 = ttk.Frame(root)
        row5.grid(row=5, column=0, columnspan=8, sticky="we", pady=(4, 4))
        ttk.Label(row5, text=t("image_store") + ":").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(row5, text=t("per_file"), value="per-file", variable=self.images_mode_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(row5, text=t("out_images"), value="out-images", variable=self.images_mode_var).pack(side=tk.LEFT)
        
        # Row 6: Path | Backup | Clear log
        row6 = ttk.Frame(root)
        row6.grid(row=6, column=0, columnspan=8, sticky="we", pady=(4, 0))
        
        # Path localized combobox with internal mapping
        path_labels = {"relative": ("相对", "Relative"), "absolute": ("绝对", "Absolute")}
        lang_code = self.lang_var.get()
        path_values = [path_labels["relative"][0] if lang_code == "zh" else path_labels["relative"][1],
                       path_labels["absolute"][0] if lang_code == "zh" else path_labels["absolute"][1]]
        current_code = self.path_mode_var.get()
        current_label = path_labels[current_code][0] if lang_code == "zh" else path_labels[current_code][1]
        self.path_display_var.set(current_label)
        
        path_frame = ttk.Frame(row6)
        path_frame.pack(side=tk.LEFT, padx=(0, 24))
        ttk.Label(path_frame, text=t("path") + ":").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(path_frame, width=10, state="readonly", values=path_values, textvariable=self.path_display_var).pack(side=tk.LEFT)
        
        def on_path_display_change(*_):
            lbl = self.path_display_var.get()
            code = None
            if lbl in (path_labels["relative"][0], path_labels["relative"][1]):
                code = "relative"
            elif lbl in (path_labels["absolute"][0], path_labels["absolute"][1]):
                code = "absolute"
            if code and code != self.path_mode_var.get():
                self.path_mode_var.set(code)
            self._refresh_display()
        self.path_display_var.trace_add("write", on_path_display_change)
        
        # Backup checkbox
        ttk.Checkbutton(row6, text=t("backup"), variable=self.backup_var).pack(side=tk.LEFT, padx=(0, 16))
        
        # Clear log checkbox
        ttk.Checkbutton(row6, text=t("clear_log"), variable=self.clear_log_var).pack(side=tk.LEFT)

        # Buttons
        btns = ttk.Frame(root)
        btns.grid(row=7, column=0, columnspan=8, sticky="w", pady=8)
        ttk.Button(btns, text=t("render"), command=self.on_render).pack(side=tk.LEFT)
        ttk.Button(btns, text=t("dry_run"), command=lambda: self.on_render(dry=True)).pack(side=tk.LEFT, padx=6)

        # Output log
        self.output = tk.Text(root, height=16)
        self.output.grid(row=8, column=0, columnspan=8, sticky="nsew")

        # Bind display behavior
        self.input_entry.bind("<FocusIn>", self._on_input_focus_in)
        self.input_entry.bind("<FocusOut>", self._on_input_focus_out)
        self.out_entry.bind("<FocusIn>", self._on_out_focus_in)
        self.out_entry.bind("<FocusOut>", self._on_out_focus_out)

    # Helpers
    def _repo_root(self) -> Path:
        # Return script directory instead of assuming repo structure
        return Path(__file__).parent

    def _to_relative(self, p: str) -> str:
        try:
            rel = os.path.relpath(p, self._repo_root())
            return os.path.normpath(rel)
        except Exception:
            return p

    def _to_absolute(self, p: str) -> str:
        abs_p = str((self._repo_root() / p).resolve()) if not Path(p).is_absolute() else p
        return os.path.normpath(abs_p)

    def _shorten(self, p: str, maxlen: int = 70) -> str:
        if len(p) <= maxlen:
            return p
        tail_len = max(20, maxlen - 10)
        return p[:3] + "..." + p[-tail_len:]

    def _refresh_display(self) -> None:
        """Refresh displayed paths in entry widgets."""
        if self.path_mode_var.get() == "relative":
            disp_in = self._to_relative(self.input_value)
            disp_out = self._to_relative(self.out_value)
        else:
            disp_in = self.input_value
            disp_out = self.out_value
        if self.input_kind == "files" and self.input_files:
            try:
                common = os.path.commonpath(self.input_files)
            except Exception:
                common = os.path.dirname(self.input_files[0])
            disp_in = os.path.normpath(common) + f" ({len(self.input_files)} {self.t('files_suffix')})"
        else:
            disp_in = os.path.normpath(disp_in)
        disp_out = os.path.normpath(disp_out)
        self.input_var.set(self._shorten(disp_in))
        self.out_dir_var.set(self._shorten(disp_out))

    def _on_input_focus_in(self, *_) -> None:
        """Show full path when input field gains focus."""
        if self.input_kind == "files" and self.input_files:
            try:
                common = os.path.commonpath(self.input_files)
            except Exception:
                common = os.path.dirname(self.input_files[0])
            full = os.path.normpath(common) + f" ({len(self.input_files)} {self.t('files_suffix')})"
        else:
            full = self._to_relative(self.input_value) if self.path_mode_var.get() == "relative" else self.input_value
        self.input_var.set(full)

    def _on_input_focus_out(self, *_) -> None:
        """Process input path when field loses focus."""
        txt = self.input_var.get().strip()
        if self.input_kind == "files":
            self.input_kind = "folder"
            self.input_files = []
        
        # Normalize path based on display mode
        if self.path_mode_var.get() == "relative":
            self.input_value = self._to_absolute(txt)
        else:
            self.input_value = os.path.normpath(txt)
        self._refresh_display()

    def _on_out_focus_in(self, *_) -> None:
        """Show full path when output field gains focus."""
        full = self._to_relative(self.out_value) if self.path_mode_var.get() == "relative" else self.out_value
        self.out_dir_var.set(full)

    def _on_out_focus_out(self, *_) -> None:
        """Process output path when field loses focus."""
        txt = self.out_dir_var.get().strip()
        if self.path_mode_var.get() == "relative":
            self.out_value = self._to_absolute(txt)
        else:
            self.out_value = os.path.normpath(txt)
        self._refresh_display()

    def on_browse_input_force(self, kind: str) -> None:
        """Browse for input folder or files."""
        cur = self.input_value
        init_dir = str(Path(cur).parent if Path(cur).is_file() else Path(cur))
        
        if kind == "folder":
            path = filedialog.askdirectory(title=self.t("select_folder"), initialdir=init_dir)
            if path:
                path = os.path.normpath(path)
                self.input_kind = "folder"
                self.input_files = []
                self.input_value = path
                p = Path(path)
                base = p if p.is_dir() else p.parent
                self.out_value = os.path.normpath(str(base) + DEFAULT_OUTPUT_SUFFIX)
                self._refresh_display()
        elif kind == "files":
            files = filedialog.askopenfilenames(
                title=self.t("select_files"), 
                filetypes=[("Markdown", "*.md *.markdown"), ("All", "*.*")], 
                initialdir=init_dir
            )
            files = list(files or [])
            if files:
                self.input_kind = "files"
                self.input_files = [os.path.normpath(f) for f in files]
                try:
                    common = os.path.commonpath(self.input_files)
                except ValueError:
                    # Files on different drives on Windows
                    common = os.path.dirname(self.input_files[0])
                self.input_value = os.path.normpath(common)
                self.out_value = os.path.normpath(common + DEFAULT_OUTPUT_SUFFIX)
                self._refresh_display()

    def on_browse_outdir(self) -> None:
        """Browse for output directory."""
        cur = self.out_value
        init_dir = str(Path(cur))
        path = filedialog.askdirectory(title=self.t("out_label"), initialdir=init_dir)
        if path:
            self.out_value = os.path.normpath(path)
            self._refresh_display()

    def write_out(self, text: str) -> None:
        """Write text to output log."""
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def build_command(self, in_path: str, dry: bool = False) -> list[str]:
        script = Path(__file__).with_name("convert_mermaid.py")
        out_path = self.out_value.strip()
        cmd = [sys.executable, str(script), "-i", in_path]
        if self.recursive_var.get():
            cmd.append("--recursive")
        if self.format_var.get():
            cmd.extend(["--format", self.format_var.get()])
        img_mode = self.images_mode_var.get()
        if img_mode == "per-file":
            cmd.extend(["--images-dir", "per-file"])
        else:
            if out_path and not out_path.lower().endswith((os.sep + "images", "/images")):
                out_path = os.path.join(out_path, "images")
            cmd.extend(["--out-dir", out_path or "images"])
        mode = self.mode_var.get()
        if mode == "export":
            cmd.append("--export")
        elif mode == "render":
            cmd.append("--render")
        elif mode == "render-keep":
            cmd.extend(["--render", "--keep-source"])
        if self.backup_var.get():
            cmd.append("--backup")
        if dry:
            cmd.append("--dry-run")
        return cmd

    def on_render(self, dry: bool = False) -> None:
        """Execute render command with optional dry-run."""
        # Safety check: warn when output equals input without backup
        if self.mode_var.get() in ("render", "render-keep") and not self.backup_var.get():
            in_path = Path(self.input_value)
            out_dir = Path(self.out_value)
            base_in = in_path if in_path.is_dir() else in_path.parent
            try:
                if out_dir.resolve() == base_in.resolve():
                    if not messagebox.askyesno(self.t("risk_title"), self.t("risk_msg")):
                        return
            except (OSError, ValueError) as e:
                print(f"Warning: Path comparison failed: {e}")
        try:
            if self.clear_log_var.get():
                self.output.configure(state=tk.NORMAL)
                self.output.delete("1.0", tk.END)
                self.output.configure(state=tk.DISABLED)
            repo_root = self._repo_root()
            if self.input_kind == "files" and self.input_files:
                for f in self.input_files:
                    cmd = self.build_command(f, dry=dry)
                    self.write_out("> " + " ".join(cmd))
                    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
                    if proc.stdout:
                        self.write_out(proc.stdout.strip())
                    if proc.stderr:
                        self.write_out(proc.stderr.strip())
            else:
                cmd = self.build_command(self.input_value, dry=dry)
                self.write_out("> " + " ".join(cmd))
                proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
                if proc.stdout:
                    self.write_out(proc.stdout.strip())
                if proc.stderr:
                    self.write_out(proc.stderr.strip())
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_profile_list(self) -> None:
        """Refresh the profile dropdown list."""
        names = sorted(self.profiles.keys())
        if names:
            self.profile_combo["values"] = names
            if not self.profile_var.get():
                self.profile_var.set(names[0])

    def on_load_profile(self) -> None:
        """Load settings from selected profile."""
        name = self.profile_var.get()
        if not name:
            return
        p = self.profiles.get(name, {})
        self.input_value = p.get("input", self.input_value)
        self.recursive_var.set(bool(p.get("recursive", False)))
        self.format_var.set(p.get("format", self.format_var.get()))
        self.out_value = p.get("out_dir", self.out_value)
        self.mode_var.set(p.get("mode", self.mode_var.get()))
        self.clear_log_var.set(bool(p.get("clear_log", True)))
        self.backup_var.set(bool(p.get("backup", True)))
        self.images_mode_var.set("per-file" if bool(p.get("per_file_images", False)) else "out-images")
        self.input_kind = "folder"
        self.input_files = []
        # Update display variables after loading profile
        if hasattr(self, "mode_display_var") and hasattr(self, "_mode_labels"):
            current_mode = self.mode_var.get()
            self.mode_display_var.set(self._mode_labels.get(current_mode, self._mode_labels["render-keep"])[0])
        self._refresh_display()

    def _get_state(self) -> dict:
        return {
            "input": self.input_value,
            "recursive": self.recursive_var.get(),
            "format": self.format_var.get(),
            "out_dir": self.out_value,
            "mode": self.mode_var.get(),
            "clear_log": self.clear_log_var.get(),
            "backup": self.backup_var.get(),
            "per_file_images": self.images_mode_var.get() == "per-file",
            "lang": self.lang_var.get(),
        }

    def on_profile_selected(self, *_) -> None:
        """Handle profile selection with dirty state check."""
        if self._last_loaded_state and self._get_state() != self._last_loaded_state:
            if not messagebox.askyesno(self.t("profile"), self.t("profile_changed")):
                if self._last_profile_name:
                    self.profile_var.set(self._last_profile_name)
                return
        self.on_load_profile()
        self._last_profile_name = self.profile_var.get()
        self._last_loaded_state = self._get_state()

    def on_save_profile(self) -> None:
        """Save current settings to profile."""
        name = self.profile_var.get()
        if not name:
            name = self.simple_prompt("Profile name")
            if not name:
                return
            self.profile_var.set(name)
        data = {
            "input": self.input_value,
            "recursive": self.recursive_var.get(),
            "format": self.format_var.get(),
            "out_dir": self.out_value,
            "mode": self.mode_var.get(),
            "clear_log": self.clear_log_var.get(),
            "backup": self.backup_var.get(),
            "per_file_images": self.images_mode_var.get() == "per-file",
            "images_dir": "",
        }
        self.profiles[name] = data
        save_profiles(self.profiles_path, self.profiles)
        self._refresh_profile_list()
        self._last_profile_name = name
        self._last_loaded_state = self._get_state()

    def on_delete_profile(self) -> None:
        """Delete the selected profile."""
        name = self.profile_var.get()
        if not name:
            return
        if messagebox.askyesno(self.t("delete"), self.t("delete_confirm").format(name=name)):
            self.profiles.pop(name, None)
            save_profiles(self.profiles_path, self.profiles)
            self.profile_var.set("")
            self._refresh_profile_list()

    def simple_prompt(self, title: str) -> str | None:
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("320x120")
        inp = tk.StringVar()
        ttk.Label(win, text=title+":").pack(pady=6)
        ent = ttk.Entry(win, textvariable=inp)
        ent.pack(padx=10, fill=tk.X)
        ent.focus_set()
        out = {"val": None}
        def ok():
            out["val"] = inp.get().strip()
            win.destroy()
        ttk.Button(win, text="OK", command=ok).pack(pady=8)
        self.wait_window(win)
        return out["val"]


    def t(self, key: str) -> str:
        lang = getattr(self, "lang_var", None).get() if hasattr(self, "lang_var") else "zh"
        try:
            return self._i18n.get(lang, self._i18n.get("zh", {})).get(key, key)
        except Exception:
            return key


if __name__ == "__main__":
    app = App()
    app.mainloop()
