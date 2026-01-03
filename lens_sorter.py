#!/usr/bin/env python3
# Lens Sorter
# Universal Photo & Video Organization Tool

"""
整理相機 (Sony, GoPro, etc.) 的照片和影片，按日期歸檔並支援詳細分類。
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path


class ProgressLogger:
    """處理 logging 和進度顯示"""
    
    def __init__(self, log_file: Path, verbose: bool = False):
        self.log_file = log_file
        self.verbose = verbose
        self.stats = {
            'photos_processed': 0,
            'videos_processed': 0,
            'errors': 0,
            'warnings': 0,
        }
        
        # 設定 file logger
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
            ]
        )
        self.logger = logging.getLogger('PhotoOrganizer')
        
        # 如果 verbose，也輸出到 console
        if verbose:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S')
            )
            self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        self.logger.info(message)
        if not self.verbose:
            print(f"  {message}")
    
    def warning(self, message: str):
        self.stats['warnings'] += 1
        self.logger.warning(message)
        if not self.verbose:
            print(f"⚠️  {message}")
    
    def error(self, message: str):
        self.stats['errors'] += 1
        self.logger.error(message)
        print(f"❌ {message}")
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def generate_report(self) -> str:
        """產生最終報告"""
        return f"""
╔════════════════════════════════════════╗
║           處理完成報告                 ║
╠════════════════════════════════════════╣
║  照片處理: {self.stats['photos_processed']:>6} 張
║  影片處理: {self.stats['videos_processed']:>6} 部
║  警告:     {self.stats['warnings']:>6} 個
║  錯誤:     {self.stats['errors']:>6} 個
╚════════════════════════════════════════╝
詳細 log: {self.log_file}
"""


class PhotoOrganizer:
    """主要的照片整理類別"""
    
    # 支援的檔案格式
    PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
    VIDEO_EXTENSIONS = {'.mp4', '.MP4', '.mov', '.MOV'}
    
    def __init__(self, input_dir: Path, output_dir: Path, dry_run: bool = False, 
                 no_thumbnail: bool = False, logger: ProgressLogger = None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.no_thumbnail = no_thumbnail
        self.logger = logger
        self.files_to_process = []  # 儲存掃描到的檔案資訊
    
    def scan_files(self) -> list:
        """掃描輸入資料夾，找出所有照片和影片"""
        files = []
        all_extensions = self.PHOTO_EXTENSIONS | self.VIDEO_EXTENSIONS
        
        # 遞迴掃描所有檔案
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in all_extensions:
                # 跳過 macOS 的 ._ 開頭檔案
                if file_path.name.startswith('._'):
                    continue
                
                file_type = 'photo' if file_path.suffix in self.PHOTO_EXTENSIONS else 'video'
                files.append({
                    'path': file_path,
                    'type': file_type,
                    'original_name': file_path.name,
                    'size': file_path.stat().st_size,
                })
        
        self.logger.info(f"找到 {len([f for f in files if f['type'] == 'photo'])} 張照片")
        self.logger.info(f"找到 {len([f for f in files if f['type'] == 'video'])} 部影片")
        
        return files
    
    def read_exif(self, file_path: Path) -> dict:
        """使用 exiftool 讀取檔案的 EXIF 資訊"""
        import subprocess
        import json
        
        try:
            # 使用 exiftool 輸出 JSON 格式
            result = subprocess.run(
                ['exiftool', '-json', '-DateTimeOriginal', '-CreateDate', 
                 '-FileModifyDate', '-Model', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.warning(f"exiftool 錯誤: {file_path.name}")
                return None
            
            data = json.loads(result.stdout)
            if not data:
                return None
            
            exif = data[0]
            
            # 優先使用 DateTimeOriginal，其次 CreateDate，最後 FileModifyDate
            datetime_str = (
                exif.get('DateTimeOriginal') or 
                exif.get('CreateDate') or 
                exif.get('FileModifyDate')
            )
            
            if not datetime_str:
                self.logger.warning(f"無法取得拍攝時間: {file_path.name}")
                return None
            
            # 解析日期時間 (格式: "2025:02:26 07:41:04" 或帶時區)
            # 移除可能的時區資訊
            datetime_str = datetime_str.split('+')[0].split('-')[0] if '+' in datetime_str or datetime_str.count('-') > 2 else datetime_str.replace(':', '-', 2)
            
            # 嘗試解析
            try:
                # 格式: "2025:02:26 07:41:04"
                dt = datetime.strptime(datetime_str.strip(), '%Y:%m:%d %H:%M:%S')
            except ValueError:
                try:
                    # 格式: "2025-02-26 07:41:04"
                    dt = datetime.strptime(datetime_str.strip(), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    self.logger.warning(f"無法解析日期格式: {datetime_str} ({file_path.name})")
                    return None
            
            return {
                'datetime': dt,
                'camera': exif.get('Model', 'Unknown'),
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"exiftool 超時: {file_path.name}")
            return None
        except Exception as e:
            self.logger.error(f"讀取 EXIF 失敗: {file_path.name} - {e}")
            return None
    
    def run(self):
        """執行整理流程"""
        mode = "[DRY-RUN] " if self.dry_run else ""
        self.logger.info(f"{mode}開始整理照片...")
        self.logger.info(f"輸入資料夾: {self.input_dir}")
        self.logger.info(f"輸出資料夾: {self.output_dir}")
        
        # Phase 2: 掃描檔案
        print("\n📂 掃描檔案中...")
        files = self.scan_files()
        
        if not files:
            self.logger.warning("沒有找到任何照片或影片")
            return
        
        # Phase 2: 讀取 EXIF
        print("\n📷 讀取 EXIF 資訊中...")
        try:
            from tqdm import tqdm
            file_iterator = tqdm(files, desc="讀取 EXIF", unit="檔案")
        except ImportError:
            self.logger.warning("tqdm 未安裝，使用簡單進度顯示")
            file_iterator = files
        
        for file_info in file_iterator:
            exif = self.read_exif(file_info['path'])
            if exif:
                file_info['datetime'] = exif['datetime']
                file_info['camera'] = exif['camera']
                file_info['new_name'] = self._generate_new_filename(file_info)
                self.logger.debug(f"{file_info['original_name']} -> {file_info['new_name']}")
            else:
                # 使用檔案修改時間作為備用
                mtime = datetime.fromtimestamp(file_info['path'].stat().st_mtime)
                file_info['datetime'] = mtime
                file_info['camera'] = 'Unknown'
                file_info['new_name'] = self._generate_new_filename(file_info)
                self.logger.warning(f"使用檔案修改時間: {file_info['original_name']}")
        
        self.files_to_process = files
        
        # 顯示掃描結果摘要
        print(f"\n✅ 掃描完成！")
        dates = set(f['datetime'].strftime('%Y-%m-%d') for f in files if 'datetime' in f)
        print(f"   跨越 {len(dates)} 個日期: {min(dates)} ~ {max(dates)}")
        
        # Phase 3: 搬移檔案
        print(f"\n📦 {'[DRY-RUN] 模擬' if self.dry_run else ''}搬移檔案中...")
        moved_count = 0
        
        for file_info in files:
            target_path = self._generate_target_path(file_info)
            file_info['target_path'] = target_path
            
            if self.dry_run:
                self.logger.debug(f"[DRY-RUN] {file_info['original_name']} -> {target_path}")
            else:
                success = self.move_file(file_info)
                if success:
                    moved_count += 1
                    if file_info['type'] == 'photo':
                        self.logger.stats['photos_processed'] += 1
                    else:
                        self.logger.stats['videos_processed'] += 1
            
            # 簡單進度顯示
            if not self.dry_run and moved_count % 100 == 0 and moved_count > 0:
                print(f"   已處理 {moved_count} 個檔案...")
        
        if self.dry_run:
            # Dry-run 模式顯示會做什麼
            print(f"\n📋 [DRY-RUN] 計畫摘要:")
            print(f"   將處理 {len([f for f in files if f['type'] == 'photo'])} 張照片")
            print(f"   將處理 {len([f for f in files if f['type'] == 'video'])} 部影片")
            
            # 顯示前 5 個範例
            print(f"\n   範例 (前 5 個):")
            for f in files[:5]:
                print(f"   📄 {f['original_name']}")
                print(f"      -> {f['target_path']}")
        else:
            print(f"\n✅ 搬移完成！共處理 {moved_count} 個檔案")
        
        # Phase 4: 產生縮圖
        if not self.no_thumbnail and not self.dry_run:
            print(f"\n🖼️  產生縮圖中...")
            thumb_count = 0
            photo_files = [f for f in files if f['type'] == 'photo']
            
            for file_info in photo_files:
                if 'target_path' in file_info:
                    success = self.generate_thumbnail(file_info['target_path'])
                    if success:
                        thumb_count += 1
                    
                    if thumb_count % 100 == 0 and thumb_count > 0:
                        print(f"   已產生 {thumb_count} 個縮圖...")
            
            print(f"✅ 縮圖產生完成！共 {thumb_count} 個")
        elif self.dry_run:
            photo_count = len([f for f in files if f['type'] == 'photo'])
            print(f"\n🖼️  [DRY-RUN] 將產生 {photo_count} 個縮圖")
        
        # Phase 5: 產生 JSON 索引
        if not self.dry_run:
            print(f"\n📋 更新索引中...")
            self.update_index(files)
            print(f"✅ 索引更新完成: _index.json")
        else:
            print(f"\n📋 [DRY-RUN] 將更新 _index.json")
        
        self.logger.info(f"{mode}整理完成！")
        
        # Phase 6: 互動式事件命名（僅非 dry-run 模式）
        if not self.dry_run and files:
            self.interactive_event_naming(files)
    
    def _generate_target_path(self, file_info: dict) -> Path:
        """計算檔案的目標路徑"""
        dt = file_info['datetime']
        file_type = file_info['type']
        
        # 結構: YYYY/MM/YYYY-MM-DD/photos/ 或 videos/
        date_folder = dt.strftime('%Y-%m-%d')
        type_folder = 'photos' if file_type == 'photo' else 'videos'
        
        target_dir = self.output_dir / dt.strftime('%Y') / dt.strftime('%m') / date_folder / type_folder
        target_path = target_dir / file_info['new_name']
        
        return target_path
    
    def move_file(self, file_info: dict) -> bool:
        """搬移並重新命名檔案"""
        import shutil
        
        source = file_info['path']
        target = file_info['target_path']
        
        try:
            # 建立目標資料夾
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # 檢查檔名衝突
            final_target = self._resolve_collision(target)
            
            # 搬移檔案
            shutil.move(str(source), str(final_target))
            self.logger.debug(f"已搬移: {source.name} -> {final_target}")
            
            # 處理 sidecar 檔案 (影片的 XML)
            if file_info['type'] == 'video':
                self._move_sidecar(source, final_target)
            
            return True
            
        except Exception as e:
            self.logger.error(f"搬移失敗: {source.name} - {e}")
            return False
    
    def _resolve_collision(self, target: Path) -> Path:
        """解決檔名衝突，加上 _1, _2 等後綴"""
        if not target.exists():
            return target
        
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_target = parent / new_name
            if not new_target.exists():
                self.logger.warning(f"檔名衝突，重新命名為: {new_name}")
                return new_target
            counter += 1
            if counter > 100:  # 防止無限迴圈
                raise Exception(f"無法解決檔名衝突: {target}")
    
    def _move_sidecar(self, source: Path, target: Path):
        """搬移影片的 sidecar 檔案 (XML)"""
        import shutil
        
        # Sony 影片的 sidecar 格式: C0001.MP4 -> C0001M01.XML
        source_stem = source.stem
        sidecar_pattern = f"{source_stem}M01.XML"
        sidecar_source = source.parent / sidecar_pattern
        
        if sidecar_source.exists():
            # 產生對應的 sidecar 目標名稱
            target_stem = target.stem
            sidecar_target = target.parent / f"{target_stem}M01.XML"
            
            try:
                shutil.move(str(sidecar_source), str(sidecar_target))
                self.logger.debug(f"已搬移 sidecar: {sidecar_source.name}")
            except Exception as e:
                self.logger.warning(f"搬移 sidecar 失敗: {sidecar_source.name} - {e}")
    
    def generate_thumbnail(self, source_path: Path, max_width: int = 300) -> bool:
        """產生縮圖，使用 macOS sips 或 Pillow"""
        import subprocess
        import shutil
        
        # 計算縮圖路徑
        thumb_dir = source_path.parent.parent / 'thumbnails'
        thumb_name = source_path.stem + '_thumb.jpg'
        thumb_path = thumb_dir / thumb_name
        
        try:
            # 建立縮圖資料夾
            thumb_dir.mkdir(parents=True, exist_ok=True)
            
            # 嘗試使用 Pillow
            try:
                from PIL import Image
                with Image.open(source_path) as img:
                    # 計算縮放比例
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    
                    # 縮放並儲存
                    img_resized = img.resize((max_width, new_height), Image.LANCZOS)
                    img_resized.save(thumb_path, 'JPEG', quality=85)
                    
                self.logger.debug(f"已產生縮圖 (Pillow): {thumb_name}")
                return True
                
            except ImportError:
                # Pillow 未安裝，使用 macOS sips
                pass
            
            # Fallback: 使用 macOS sips
            # 先複製原始檔案
            shutil.copy2(str(source_path), str(thumb_path))
            
            # 使用 sips 縮放
            result = subprocess.run(
                ['sips', '-Z', str(max_width), str(thumb_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.debug(f"已產生縮圖 (sips): {thumb_name}")
                return True
            else:
                self.logger.warning(f"sips 失敗: {source_path.name}")
                # 刪除失敗的檔案
                if thumb_path.exists():
                    thumb_path.unlink()
                return False
                
        except Exception as e:
            self.logger.warning(f"產生縮圖失敗: {source_path.name} - {e}")
            return False
    
    def update_index(self, files: list):
        """更新 _index.json 索引檔"""
        import json
        
        index_path = self.output_dir / '_index.json'
        
        # 讀取現有索引（如果存在）
        existing_index = {
            'last_updated': None,
            'total_photos': 0,
            'total_videos': 0,
            'files': [],
            'events': {}
        }
        
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    existing_index = json.load(f)
                self.logger.debug(f"讀取現有索引: {len(existing_index.get('files', []))} 個檔案")
            except Exception as e:
                self.logger.warning(f"讀取索引失敗，將重新建立: {e}")
        
        # 建立現有檔案的快速查找表（用原始檔名作為 key）
        existing_files = {f['original_name']: f for f in existing_index.get('files', [])}
        
        # 新增/更新檔案記錄
        for file_info in files:
            if 'target_path' not in file_info:
                continue
            
            # 計算相對路徑和縮圖路徑
            target_path = file_info['target_path']
            rel_path = str(target_path.relative_to(self.output_dir))
            
            thumb_path = None
            if file_info['type'] == 'photo':
                thumb_dir = target_path.parent.parent / 'thumbnails'
                thumb_name = target_path.stem + '_thumb.jpg'
                thumb_full = thumb_dir / thumb_name
                if thumb_full.exists():
                    thumb_path = str(thumb_full.relative_to(self.output_dir))
            
            file_record = {
                'original_name': file_info['original_name'],
                'new_name': file_info['new_name'],
                'path': rel_path,
                'thumbnail': thumb_path,
                'datetime': file_info['datetime'].isoformat(),
                'type': file_info['type'],
                'size_bytes': file_info['size'],
                'camera': file_info.get('camera', 'Unknown'),
            }
            
            # 更新或新增
            existing_files[file_info['original_name']] = file_record
        
        # 重建索引
        all_files = list(existing_files.values())
        all_files.sort(key=lambda x: x['datetime'])
        
        new_index = {
            'last_updated': datetime.now().isoformat(),
            'total_photos': len([f for f in all_files if f['type'] == 'photo']),
            'total_videos': len([f for f in all_files if f['type'] == 'video']),
            'files': all_files,
            'events': existing_index.get('events', {})
        }
        
        # 寫入索引
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(new_index, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已更新索引: {len(all_files)} 個檔案")
        except Exception as e:
            self.logger.error(f"寫入索引失敗: {e}")
    
    def interactive_event_naming(self, files: list):
        """互動式為日期加上事件名稱"""
        import json
        import shutil
        
        # 統計每個日期的檔案數量
        date_counts = {}
        for f in files:
            if 'datetime' not in f:
                continue
            date_str = f['datetime'].strftime('%Y-%m-%d')
            if date_str not in date_counts:
                date_counts[date_str] = {'photos': 0, 'videos': 0}
            if f['type'] == 'photo':
                date_counts[date_str]['photos'] += 1
            else:
                date_counts[date_str]['videos'] += 1
        
        if not date_counts:
            return
        
        print("\n" + "=" * 50)
        print("  📅 事件命名（選填）")
        print("=" * 50)
        print("  為日期加上事件名稱，例如「京都旅行」")
        print("  直接按 Enter 跳過，輸入 'q' 結束")
        print("=" * 50 + "\n")
        
        # 讀取現有索引
        index_path = self.output_dir / '_index.json'
        existing_events = {}
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    idx = json.load(f)
                    existing_events = idx.get('events', {})
            except:
                pass
        
        events_updated = False
        
        for date_str in sorted(date_counts.keys()):
            counts = date_counts[date_str]
            
            # 檢查是否已有事件名稱
            if date_str in existing_events:
                print(f"  {date_str}: 已命名為「{existing_events[date_str]}」")
                continue
            
            # 顯示統計
            stats_parts = []
            if counts['photos'] > 0:
                stats_parts.append(f"{counts['photos']} 張照片")
            if counts['videos'] > 0:
                stats_parts.append(f"{counts['videos']} 部影片")
            stats = "、".join(stats_parts)
            
            try:
                user_input = input(f"  {date_str} ({stats}) 事件名稱？[Enter 跳過]: ").strip()
            except EOFError:
                # 非互動模式
                break
            
            if user_input.lower() == 'q':
                break
            
            if not user_input:
                continue
            
            # 儲存事件名稱
            existing_events[date_str] = user_input
            events_updated = True
            
            # 重新命名日期資料夾
            self._rename_date_folder(date_str, user_input)
            
            self.logger.info(f"已命名: {date_str} -> {user_input}")
            print(f"  ✅ 已命名「{user_input}」")
        
        # 更新索引中的事件
        if events_updated:
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    idx = json.load(f)
                idx['events'] = existing_events
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(idx, f, ensure_ascii=False, indent=2)
                self.logger.info(f"已更新索引中的事件記錄")
            except Exception as e:
                self.logger.warning(f"更新索引事件失敗: {e}")
        
        print()
    
    def _rename_date_folder(self, date_str: str, event_name: str):
        """將日期資料夾重新命名為包含事件名稱"""
        import shutil
        
        # 解析日期
        year, month, day = date_str.split('-')
        
        # 舊資料夾路徑
        old_folder = self.output_dir / year / month / date_str
        
        if not old_folder.exists():
            self.logger.warning(f"資料夾不存在: {old_folder}")
            return
        
        # 新資料夾名稱
        new_folder_name = f"{date_str}_{event_name}"
        new_folder = self.output_dir / year / month / new_folder_name
        
        try:
            old_folder.rename(new_folder)
            self.logger.debug(f"已重新命名資料夾: {date_str} -> {new_folder_name}")
        except Exception as e:
            self.logger.warning(f"重新命名資料夾失敗: {e}")
    
    def _generate_new_filename(self, file_info: dict) -> str:
        """產生新檔名: YYYYMMDD_HHMMSS_原始編號.副檔名"""
        dt = file_info['datetime']
        original_stem = file_info['path'].stem  # 不含副檔名
        suffix = file_info['path'].suffix.upper()  # 統一大寫副檔名
        
        return f"{dt.strftime('%Y%m%d_%H%M%S')}_{original_stem}{suffix}"


def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description='Lens Sorter - 相機/GoPro 照片整理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  %(prog)s --dry-run                    # 模擬執行，不實際搬移
  %(prog)s --input ./inbox              # 指定輸入資料夾
  %(prog)s --verbose                    # 顯示詳細輸出
  %(prog)s --no-thumbnail               # 跳過縮圖產生
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('./_inbox'),
        help='輸入資料夾路徑 (預設: ./_inbox)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('.'),
        help='輸出根目錄 (預設: 當前目錄)'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='模擬執行，只輸出計畫，不實際搬移檔案'
    )
    
    parser.add_argument(
        '--no-thumbnail',
        action='store_true',
        help='跳過縮圖產生'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='顯示詳細輸出到 console'
    )
    
    return parser.parse_args()


def main():
    """主程式入口"""
    args = parse_args()
    
    # 驗證輸入資料夾存在
    if not args.input.exists():
        print(f"❌ 錯誤: 輸入資料夾不存在: {args.input}")
        print(f"   請先建立資料夾並放入要整理的照片")
        sys.exit(1)
    
    # 初始化 logger
    log_file = args.output / 'organize.log'
    logger = ProgressLogger(log_file, verbose=args.verbose)
    
    # 顯示啟動資訊
    print("=" * 50)
    print("  Lens Sorter - 相機/GoPro 歸檔工具")
    print("=" * 50)
    if args.dry_run:
        print("  🔍 模式: DRY-RUN (不會實際搬移檔案)")
    print(f"  📂 輸入: {args.input.absolute()}")
    print(f"  📂 輸出: {args.output.absolute()}")
    print(f"  📝 Log:  {log_file.absolute()}")
    print("=" * 50)
    print()
    
    # 執行整理
    organizer = PhotoOrganizer(
        input_dir=args.input,
        output_dir=args.output,
        dry_run=args.dry_run,
        no_thumbnail=args.no_thumbnail,
        logger=logger
    )
    
    try:
        organizer.run()
        print(logger.generate_report())
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷執行")
        logger.warning("使用者中斷執行 (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.error(f"未預期的錯誤: {e}")
        raise


if __name__ == '__main__':
    main()
