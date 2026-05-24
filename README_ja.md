# Satyros v0.3.2

Satyrosはネットワーク管理ツールです。TFTP、FTP、SFTP、Syslog、SNMPといった主要なネットワークサービスを、単一のグラフィカルなインターフェースで実行・管理することができます。

## 機能

- **TFTPサーバー & クライアント**
  - リスニングIP・ポート・ルートディレクトリを指定してTFTPサーバーを起動できます。
  - サーバー上のアクティブな転送状況をリアルタイムで確認できます。
  - 内蔵のTFTPクライアントを使って、ファイルの取得（Get）・送信（Put）が行えます。

- **FTP / SFTP / FTPSサーバー**
  - 標準のFTPサーバーを起動できます。
  - 自動生成された自己署名証明書を用いた FTPS（Implicit TLS）にも対応しています。
  - `paramiko` を利用した安全なSFTPサーバーの起動も可能です。
  - ユーザー認証情報とディレクトリアクセス設定をFTP/SFTPで共有して管理できます。

- **Syslogサーバー**
  - Syslogメッセージをリアルタイムで受信・表示します。
  - 重要度（Severity）に応じた色分け表示（Emergency/Alert/Critical＝赤、Warning＝黄、Info＝白）。
  - ログのリアルタイム検索・フィルタリング機能。
  - ログをテキストファイルへエクスポートする機能。
  - `syslog.log` の日次自動ローテーション。

- **SNMPマネージャー & トラップレシーバー**
  - **トラップレシーバー**: SNMPトラップ（v1/v2c/v3）を受信します。MIB辞書を使用してOIDを自動的に人間が読みやすい形式にデコードします。トラップをCSVファイルへエクスポートできます。
  - **SNMPマネージャー**: SNMPv3の認証・暗号化プロトコルに対応した `Get` および `Walk` クエリを実行できます。

- **モダンなGUI**
  - Flet を使用して構築された、クリーンでレスポンシブな堅牢なユーザーインターフェース。

## ソースコードから実行する方法

必要な依存関係をインストールします：
```bash
pip install -r requirements.txt
```

アプリケーションを起動します：
```bash
python main.py
```

## ビルド方法

SatyrosをスタンドアロンのEXEファイルにコンパイルするには、Flet CLIを使用します：
```bash
flet pack main.py --icon icon.ico --name Satyros --product-name Satyros --product-version 0.3.2 --file-version 0.3.2.0 --file-description Satyros --company-name Satyros --copyright "2026 Satyros" --add-data "assets:assets"
```

## クレジット
- mizuki-py
- Antigravity(Gemini, Claude)
