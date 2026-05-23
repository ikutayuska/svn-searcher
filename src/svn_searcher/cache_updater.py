import csv
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class SVNCacheUpdater:
    def __init__(self, svn_url: str, cache_file: str, rev_file: str):
        self.svn_url = svn_url.rstrip("/")
        self.cache_file = Path(cache_file)
        self.rev_file = Path(rev_file)

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.rev_file.parent.mkdir(parents=True, exist_ok=True)

    def get_last_revision(self) -> int:
        if not self.rev_file.exists():
            self.rev_file.write_text("0", encoding="utf-8")

        text = self.rev_file.read_text(encoding="utf-8").strip()
        return int(text) if text else 0

    def save_last_revision(self, revision: int) -> None:
        self.rev_file.write_text(str(revision), encoding="utf-8")

    def get_latest_revision(self) -> int:
        result = subprocess.run(
            ["svn", "info", self.svn_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=30
        )

        for line in result.stdout.splitlines():
            if line.startswith("Revision:"):
                return int(line.split(":", 1)[1].strip())

        return 0

    def run_svn_info_recursive(self) -> str:
        result = subprocess.run(
            ["svn", "info", "-R", self.svn_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=300
        )
        return result.stdout

    def parse_svn_info(self, text: str) -> List[Tuple[str, str]]:
        entries = []

        current_url = None
        current_date = None

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("URL:"):
                current_url = line.split(":", 1)[1].strip()

            elif line.startswith("Last Changed Date:"):
                match = re.search(
                    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
                    line
                )
                current_date = match.group(0) if match else ""

            elif line == "":
                if current_url and current_date:
                    entries.append((current_url, current_date))

                current_url = None
                current_date = None

        if current_url and current_date:
            entries.append((current_url, current_date))

        return entries

    def save_cache_csv(self, entries: List[Tuple[str, str]]) -> None:
        with self.cache_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["path", "timestamp"])
            writer.writerows(entries)

    def load_cache_csv(self) -> Dict[str, str]:
        if not self.cache_file.exists():
            return {}

        with self.cache_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                row["path"]: row.get("timestamp", "")
                for row in reader
                if row.get("path")
            }

    def update_cache(self) -> None:
        last_rev = self.get_last_revision()
        latest_rev = self.get_latest_revision()

        if last_rev >= latest_rev:
            print(f"{self.svn_url} キャッシュは最新です")
            return

        print(f"{self.svn_url} キャッシュ更新中...")

        info_text = self.run_svn_info_recursive()
        entries = self.parse_svn_info(info_text)

        self.save_cache_csv(entries)
        self.save_last_revision(latest_rev)

        print(f"キャッシュ更新完了: {self.cache_file} ({len(entries)} 件)")