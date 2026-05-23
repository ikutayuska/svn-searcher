# SVN Searcher

SVN 上のファイルを検索し、選択したファイルをエクスポートする GUI ツールです。

## 公開リポジトリ向け運用


1. `repositories.example.json` をコピーして `repositories.json` を作成
2. `repositories.json` に SVN 情報を設定
3. `repositories.json` は `.gitignore` により Git 追跡対象外

```bash
cp repositories.example.json repositories.json
```

## 実行

```bash
python search_svn_gui.py
```
