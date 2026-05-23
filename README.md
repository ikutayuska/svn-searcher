# SVN Searcher

SVN 上のファイルを検索し、選択したファイルをエクスポートする GUI ツールです。

## フォルダー構成

```text
SVN_Searcher/
├── config/
│   └── repositories.example.json
├── scripts/
│   └── run_gui.py
└── src/
    └── svn_searcher/
        ├── cache_updater.py
        ├── gui.py
        └── __init__.py
```

## 公開リポジトリ向け運用

1. `config/repositories.example.json` をコピーして `config/repositories.json` を作成
2. `config/repositories.json` に SVN 情報を設定
3. `config/repositories.json` は `.gitignore` により Git 追跡対象外

```bash
cp config/repositories.example.json config/repositories.json
```

## 実行

```bash
PYTHONPATH=src python scripts/run_gui.py
```
