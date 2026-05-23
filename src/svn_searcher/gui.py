import csv
import json
import logging
import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Dict, List, Tuple
from urllib.parse import unquote

from svn_searcher.cache_updater import SVNCacheUpdater


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
LOG_FOLDER = RUNTIME_DIR / "logs"
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FOLDER / "svn_gui.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SVNFileSearcherGUI:
    OUTPUT_FOLDER = RUNTIME_DIR / "Exported_Files"
    CONFIG_FILE = PROJECT_ROOT / "config" / "repositories.json"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SVN Searcher")
        self.root.geometry("1100x700")

        self.matches: List[Tuple[str, str]] = []
        self.display_to_path: Dict[str, str] = {}
        self.repositories = self.load_repositories()

        self.OUTPUT_FOLDER.mkdir(exist_ok=True)

        self.create_widgets()

    def create_widgets(self) -> None:
        top_frame = ttk.Frame(self.root)
        top_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(top_frame, text="リポジトリ:").pack(side="left")

        repo_names = list(self.repositories.keys())
        self.repo_var = tk.StringVar(value=repo_names[0])
        for repo_name in repo_names:
            ttk.Radiobutton(
                top_frame,
                text=repo_name,
                variable=self.repo_var,
                value=repo_name
            ).pack(side="left", padx=5)

        ttk.Button(
            top_frame,
            text="キャッシュ更新",
            command=self.update_cache_files
        ).pack(side="left", padx=15)

        keyword_frame = ttk.Frame(self.root)
        keyword_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(keyword_frame, text="キーワード:").pack(side="left")

        self.keyword_entry = ttk.Entry(keyword_frame, width=60)
        self.keyword_entry.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(
            keyword_frame,
            text="検索",
            command=self.search_cache
        ).pack(side="left", padx=5)

        result_frame = ttk.Frame(self.root)
        result_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.result_listbox = tk.Listbox(
            result_frame,
            selectmode="extended",
            font=("Meiryo", 11),
            height=25,
            width=120
        )
        self.result_listbox.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.result_listbox.yview
        )
        y_scroll.pack(side="right", fill="y")

        x_scroll = ttk.Scrollbar(
            self.root,
            orient="horizontal",
            command=self.result_listbox.xview
        )
        x_scroll.pack(fill="x", padx=10)

        self.result_listbox.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="選択ファイルをエクスポート",
            command=self.export_selected
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="結果クリア",
            command=self.clear_results
        ).pack(side="left", padx=5)

    def get_repo_config(self) -> dict:
        return self.repositories[self.repo_var.get()]

    def load_repositories(self) -> Dict[str, Dict[str, str]]:
        if not self.CONFIG_FILE.exists():
            raise FileNotFoundError(
                f"{self.CONFIG_FILE} が見つかりません。"
                " config/repositories.example.json をコピーして作成してください。"
            )

        with self.CONFIG_FILE.open("r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict) or not config:
            raise ValueError("repositories.json の形式が不正です。")

        required_keys = {"url", "cache", "rev"}
        for name, repo in config.items():
            if not isinstance(repo, dict) or not required_keys.issubset(repo):
                raise ValueError(f"{name} の設定に url/cache/rev が必要です。")

        return config

    def update_cache_files(self) -> None:
        try:
            logger.info("キャッシュ更新開始")

            for name, config in self.repositories.items():
                logger.info(f"{name} 更新開始")

                updater = SVNCacheUpdater(
                    config["url"],
                    config["cache"],
                    config["rev"]
                )
                updater.update_cache()

                logger.info(f"{name} 更新完了")

            messagebox.showinfo("完了", "キャッシュ更新が完了しました。")

        except subprocess.TimeoutExpired:
            logger.exception("キャッシュ更新タイムアウト")
            messagebox.showinfo("Timeout", "SVNサーバーが応答しませんでした。")

        except subprocess.CalledProcessError as e:
            logger.exception("SVNコマンドエラー")
            messagebox.showinfo(
                "SVNエラー",
                f"SVNコマンドでエラーが発生しました。\n\n{e.stderr}"
            )

        except Exception as e:
            logger.exception("予期せぬエラー")
            messagebox.showinfo("エラー", f"予期せぬエラー: {e}")

    def load_cache(self, cache_file: str) -> List[Tuple[str, str]]:
        path = Path(cache_file)

        if not path.exists():
            raise FileNotFoundError(cache_file)

        entries = []

        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                svn_path = row.get("path", "").strip()
                timestamp = row.get("timestamp", "").strip()

                if svn_path:
                    entries.append((svn_path, timestamp))

        return entries

    def search_cache(self) -> None:
        config = self.get_repo_config()
        cache_file = config["cache"]

        keywords = self.keyword_entry.get().split()

        if not keywords:
            messagebox.showinfo("入力エラー", "キーワードを入力してください。")
            return

        try:
            entries = self.load_cache(cache_file)

            matched = []
            for path, timestamp in entries:
                decoded_path = unquote(path)

                if "削除予定" in decoded_path:
                    continue

                if all(keyword in decoded_path for keyword in keywords):
                    matched.append((decoded_path, timestamp))

            self.matches = sorted(matched, key=lambda x: x[0])
            self.show_results()

            logger.info(
                f"検索完了 repo={self.repo_var.get()}, "
                f"keywords={keywords}, count={len(self.matches)}"
            )

            if not self.matches:
                messagebox.showinfo("検索結果", "ファイルが見つかりませんでした。")

        except FileNotFoundError:
            messagebox.showinfo(
                "エラー",
                f"キャッシュファイルが見つかりません。\n{cache_file}"
            )

        except Exception as e:
            logger.exception("検索エラー")
            messagebox.showinfo("エラー", f"検索中にエラーが発生しました: {e}")

    def make_display_text(self, path: str, timestamp: str) -> str:
        parts = Path(path.replace("\\", "/")).parts

        if len(parts) >= 2:
            short_name = "/".join(parts[-2:])
        else:
            short_name = os.path.basename(path)

        if timestamp:
            return f"{short_name}    [{timestamp}]"

        return short_name

    def show_results(self) -> None:
        self.result_listbox.delete(0, tk.END)
        self.display_to_path.clear()

        for index, (path, timestamp) in enumerate(self.matches, start=1):
            display = self.make_display_text(path, timestamp)

            # 同じファイル名が複数ある場合に上書きされないよう番号を付ける
            display_key = f"{index}. {display}"

            self.result_listbox.insert(tk.END, display_key)
            self.display_to_path[display_key] = path

    def export_selected(self) -> None:
        selected_indices = self.result_listbox.curselection()

        if not selected_indices:
            messagebox.showinfo("未選択", "ファイルを選択してください。")
            return

        for i in selected_indices:
            display_key = self.result_listbox.get(i)
            full_path = self.display_to_path.get(display_key)

            if not full_path:
                continue

            full_path = unquote(full_path)

            logger.info(f"エクスポート開始: {full_path}")

            try:
                result = subprocess.run(
                    ["svn", "export", "--force", full_path, str(self.OUTPUT_FOLDER)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=20
                )

                if result.returncode != 0:
                    logger.error(f"エクスポート失敗: {full_path}")
                    logger.error(result.stderr)

                    messagebox.showinfo(
                        "エクスポート失敗",
                        f"{full_path} のエクスポートに失敗しました。\n\n"
                        f"エラー内容:\n{result.stderr}"
                    )
                    return

                logger.info(f"エクスポート成功: {full_path}")

            except subprocess.TimeoutExpired:
                logger.exception("エクスポートタイムアウト")
                messagebox.showinfo(
                    "Timeout",
                    "サーバーが応答しませんでした。"
                )
                return

            except Exception as e:
                logger.exception("予期せぬエクスポートエラー")
                messagebox.showinfo(
                    "エラー",
                    f"予期せぬエラーが発生しました。\n\n{e}"
                )
                return

        messagebox.showinfo(
            "完了",
            f"エクスポート完了！\n保存先: {self.OUTPUT_FOLDER.resolve()}"
        )

    def clear_results(self) -> None:
        self.matches.clear()
        self.display_to_path.clear()
        self.result_listbox.delete(0, tk.END)


def main() -> None:
    root = tk.Tk()
    try:
        SVNFileSearcherGUI(root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        messagebox.showerror("設定エラー", str(e))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
