# RaspiBlePeripheral — Raspberry Pi BLE ペリフェラル（Peripheral）

Raspberry Pi を BLE（Bluetooth Low Energy）のペリフェラルデバイスとして動作させるPythonスクリプトです。
センサー値やデータをアドバタイズ・送信します。

---

## 概要

このプロジェクトは `RaspiBle`（セントラル側）とセットで動作します。

```
[RaspiBlePeripheral]  ──BLE──▶  [RaspiBle]
   Raspberry Pi                  Raspberry Pi
   （送信側）                    （受信・制御側）
```

---

## 主な機能

- BLE ペリフェラルとしてのアドバタイズ（存在通知）
- サービス・キャラクタリスティックの定義
- セントラルデバイスからの接続受け入れ
- データの送信（Notify / Read 対応）

---

## 技術スタック

| カテゴリ | 使用技術 |
|----------|---------|
| 言語 | Python 3 |
| BLEライブラリ | bluepy / bluezdbus |
| 動作ハードウェア | Raspberry Pi（Bluetooth内蔵モデル推奨） |

---

## 動作環境

- Raspberry Pi 3B+ / 4 / Zero 2W 以上推奨
- Raspberry Pi OS (Bullseye 以降)
- Python 3.8 以上
- Bluetooth内蔵 または USB Bluetoothアダプタ

---

## セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/TarkMatter/RaspiBlePeripheral.git
cd RaspiBlePeripheral

# 2. 依存パッケージのインストール
pip install bluezdbus

# 3. bluetoothサービスの確認
sudo systemctl status bluetooth

# 4. スクリプトを実行（root権限が必要な場合あり）
sudo python main.py
```

---

## 関連リポジトリ

- [RaspiBle](https://github.com/TarkMatter/RaspiBle) — セントラル（受信・制御）側の実装

---

## 注意事項

- ペリフェラルとして動作させるには BlueZ 5.50 以降を推奨します
- 一部の Raspberry Pi OS バージョンでは `bluetoothd` の設定変更が必要な場合があります
- 本リポジトリはBLE通信の学習・プロトタイプ用途を想定しています
