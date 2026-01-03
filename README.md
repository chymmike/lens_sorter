# Lens Sorter 📸

**Your universal tool to sort memories from every lens.**

這是一個通用型的 Python 照片與影片整理工具，專為 **Sony Alpha 系列**、**GoPro** 以及各種數位相機設計。

它可以自動讀取記憶卡中的 EXIF 資訊，將混亂的檔案按「年/月/日期」歸檔，並支援產生縮圖與 AI 索引。對於 GoPro，它會自動只保留高品質的 `.MP4` 影片，忽略多餘的 `.THM` 與 `.LRV` 檔案。

## ✨ 主要功能

- **通用歸檔**：將照片/影片移動到 `YYYY/MM/YYYY-MM-DD` 結構（支援 Sony, GoPro, iPhone 等）。
- **GoPro 優化**：自動過濾 GoPro 的 `.THM` (縮圖) 與 `.LRV` (低畫質預覽) 檔，只保留主影片。
- **重新命名**：檔名標準化為 `YYYYMMDD_HHMMSS_原始檔名.JPG`，避免檔名衝突。
- **預覽縮圖**：自動產生 300px 的 JPG 縮圖，方便快速預覽。
- **AI 索引**：產生 `_index.json`，讓未來的 AI 代理可以快速讀取照片庫結構。
- **事件命名**：整理完後支援互動式命名（例如輸入「京都旅行」，資料夾即自動更名）。
- **Sidecar 支援**：自動處理 Sony 影片的 `.XML` 伴隨檔案。

## 🚀 安裝與設定

本程式需要 **Python 3.9** 或以上版本。

### 1. 安裝依賴套件

請在你的終端機 (Terminal) 執行：

```bash
pip3 install tqdm Pillow
```

> **注意**：如果你在 macOS 遇到「externally-managed-environment」錯誤，請加上參數：
> ```bash
> pip3 install tqdm Pillow --break-system-packages
> ```

---

## 📖 使用方式

### 情境：將相機記憶卡整理到外接硬碟

假設你將此工具放在 `~/Projects/Lens-Sorter`，而你要整理記憶卡中的照片到外接硬碟。

#### 1. 準備檔案
建議先將記憶卡的所有檔案複製到一個暫存資料夾（Inbox），以確保安全。

#### 2. 執行整理
打開終端機，執行以下指令：

```bash
cd ~/Projects/Lens-Sorter

# 格式：python3 lens_sorter.py --input "來源路徑" --output "目的地路徑"
python3 lens_sorter.py \
  --input "/path/to/your/sd_card_backup" \
  --output "/path/to/your/photo_archive"
```

**範例：**
```bash
python3 lens_sorter.py --input "./_inbox" --output "/Volumes/MyHardDrive/Photos"
```

#### 3. 常用參數

*   **`--dry-run`**：  
    **強烈建議首次執行使用！** 只會模擬執行過程，不會真的搬移檔案。
    ```bash
    python3 lens_sorter.py --dry-run --input ... --output ...
    ```

*   **`--no-thumbnail`**：  
    如果你不想產生縮圖，可以加上此參數加快速度。
    ```bash
    python3 lens_sorter.py --no-thumbnail ...
    ```

---

## 📂 資料夾結構範例

執行後，你的目標資料夾 (`--output`) 會呈現以下結構：

```text
/path/to/your/archive/
├── _index.json                 # [重要] 檔案索引資料庫 (AI 用)
├── organize.log                # 執行紀錄檔
├── 2024/
│   └── 12/
│       └── 2024-12-27_Trip_to_Kyoto/ # (事件名稱可互動輸入)
│           ├── photos/
│           │   ├── 20241227_101010_DSC00123.JPG
│           │   └── ...
│           ├── videos/
│           │   ├── 20241227_102020_GX010012.MP4  # GoPro 影片
│           │   └── 20241227_102020_C0012.MP4     # Sony 影片
│           └── thumbnails/     # 縮圖資料夾
│               └── ...
└── 2025/
    └── ...
```

## 🛠️ 常見問題

**Q: GoPro 的 `.THM` 和 `.LRV` 檔案去哪了？**  
A: `Lens Sorter` 預設會忽略這些檔案。它們是 GoPro 機身回放用的低畫質預覽檔，在電腦上歸檔通常不需要，忽略它們可以節省大量空間並讓資料夾更整潔。

**Q: `_index.json` 是什麼？**  
A: 這是整個照片庫的「目錄」。當你想用 AI 來搜尋照片時，AI 只需要讀取這個小檔案，就能知道你有什麼照片、放在哪裡，而不用掃描幾萬個檔案。請務必保留它，並隨照片備份。

**Q: 如果重複執行會怎樣？**  
A: 程式會自動偵測檔名衝突。如果檔案已存在，新檔案會自動加上 `_1`, `_2` 後綴，不會覆蓋舊檔案。

---

## 👤 作者

**Mike Chen**
- Website: [chymmike.com](https://chymmike.com)
- GitHub: [@chymmike](https://github.com/chymmike)
