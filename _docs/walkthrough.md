# Sony A6400 Photo Organization Tool - Walkthrough

## 完成摘要

成功建立了一個可重複使用的 Python 照片整理工具，包含 6 個功能模組。

---

## 使用方式

```bash
# 1. 把記憶卡檔案複製到 _inbox/
cp -r /Volumes/SDCARD/DCIM/100MSDCF/* /Volumes/Crucial\ X6/A6400/_inbox/

# 2. 先 dry-run 確認
python3 organize_photos.py --dry-run

# 3. 正式執行
python3 organize_photos.py

# 4. 程式會問你要不要為日期加上事件名稱（選填）
```

---

## 實現的功能

| 功能 | 狀態 |
|------|------|
| CLI 參數 (`--dry-run`, `--verbose`, `--no-thumbnail`) | ✅ |
| 掃描 JPG/MP4 檔案 | ✅ |
| 讀取 EXIF 拍攝時間 | ✅ |
| 重新命名 (`20250226_074104_A6401534.JPG`) | ✅ |
| 按日期分類 (`2025/02/2025-02-26/photos/`) | ✅ |
| 產生 300px 縮圖 | ✅ (使用 macOS sips) |
| 產生 `_index.json` 索引 | ✅ |
| 互動式事件命名 | ✅ |
| 檔名衝突處理 | ✅ |
| Sidecar XML 處理 | ✅ |
| Log 記錄 (`organize.log`) | ✅ |

---

## 最終目錄結構

```
/Volumes/Crucial X6/A6400/
├── organize_photos.py          ← 主程式
├── _inbox/                     ← 放入待整理檔案
├── _index.json                 ← AI 可讀索引
├── organize.log                ← 操作記錄
├── _docs/                      ← 開發文件
│   ├── implementation_plan.md
│   └── task.md
└── 2025/
    └── 02/
        └── 2025-02-26/
            ├── photos/
            │   └── 20250226_074104_A6401534.JPG
            └── thumbnails/
                └── 20250226_074104_A6401534_thumb.jpg
```

---

## 測試結果

- ✅ 5 張照片成功處理
- ✅ 縮圖正確產生 (15MB → 25KB)
- ✅ `_index.json` 格式正確
- ✅ 互動式事件命名正常運作

## GoPro 支援與問題排除

1. **時間飄移修正**
   - 發現部分 GoPro 影片因相機重置導致日期錯誤（顯示為 2016-01-02）。
   - 使用 `fix_time.py` 腳本，透過 `exiftool` 進行批次時間平移 (+7年 9個多月)，成功將日期對齊回 2023 年。
2. **檔案處理**
   - 自動忽略 GoPro 的 `.THM`/`.LRV` 暫存檔。
   - 保留 GoPro 原始編號 (e.g. `GX012615`) 於新檔名中，確保檔案關聯性。

