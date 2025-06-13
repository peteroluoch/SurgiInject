"""
Tests for backup engine functionality
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import patch

from engine.backup_engine import (
    create_backup,
    list_backups,
    restore_backup,
    restore_latest_backup,
    get_backup_stats,
    cleanup_old_backups,
    get_backup_dir,
    ensure_backup_dir
)


class TestBackupEngine:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.py"
        
        # Create test file
        with open(self.test_file, 'w') as f:
            f.write("def hello():\n    print('Hello, World!')\n")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_get_backup_dir(self):
        """Test backup directory path resolution"""
        backup_dir = get_backup_dir(self.temp_dir)
        expected = Path(self.temp_dir) / ".surgi_backups"
        assert backup_dir == expected
    
    def test_ensure_backup_dir(self):
        """Test backup directory creation"""
        backup_dir = get_backup_dir(self.temp_dir)
        ensure_backup_dir(backup_dir)
        assert backup_dir.exists()
        assert backup_dir.is_dir()
    
    def test_create_backup_success(self):
        """Test successful backup creation"""
        backup_path = create_backup(str(self.test_file), self.temp_dir)
        
        # Check backup file exists
        assert Path(backup_path).exists()
        
        # Check backup content matches original
        with open(self.test_file, 'r') as f:
            original_content = f.read()
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        assert backup_content == original_content
        
        # Check backup directory structure
        backup_dir = get_backup_dir(self.temp_dir)
        assert backup_dir.exists()
    
    def test_create_backup_file_not_found(self):
        """Test backup creation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            create_backup("nonexistent.py", self.temp_dir)
    
    def test_list_backups_empty(self):
        """Test listing backups when none exist"""
        backups = list_backups("test.py", self.temp_dir)
        assert backups == []
    
    def test_list_backups_with_files(self):
        """Test listing backups when they exist"""
        # Create some backup files
        backup_dir = get_backup_dir(self.temp_dir)
        backup_dir.mkdir(exist_ok=True)
        
        (backup_dir / "test.py.20250613_120000.bak").touch()
        (backup_dir / "test.py.20250613_130000.bak").touch()
        (backup_dir / "other.py.20250613_140000.bak").touch()
        
        backups = list_backups("test.py", self.temp_dir)
        assert len(backups) == 2
        assert all("test.py" in backup for backup in backups)
        # Should be sorted newest first
        assert backups[0] > backups[1]
    
    def test_restore_backup_success(self):
        """Test successful backup restoration"""
        # Create backup
        backup_path = create_backup(str(self.test_file), self.temp_dir)
        
        # Modify original file
        with open(self.test_file, 'w') as f:
            f.write("def modified():\n    print('Modified!')\n")
        
        # Restore from backup
        backup_filename = Path(backup_path).name
        success = restore_backup(str(self.test_file), backup_filename, self.temp_dir)
        
        assert success is True
        
        # Check file was restored
        with open(self.test_file, 'r') as f:
            content = f.read()
        assert "Hello, World!" in content
        assert "Modified!" not in content
    
    def test_restore_backup_file_not_found(self):
        """Test restoration with non-existent backup"""
        success = restore_backup(str(self.test_file), "nonexistent.bak", self.temp_dir)
        assert success is False
    
    def test_restore_latest_backup(self):
        """Test restoration from latest backup"""
        # Create multiple backups
        backup_dir = get_backup_dir(self.temp_dir)
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup files with different timestamps
        (backup_dir / "test.py.20250613_120000.bak").write_text("old content")
        (backup_dir / "test.py.20250613_130000.bak").write_text("new content")
        
        # Modify original file
        with open(self.test_file, 'w') as f:
            f.write("current content")
        
        # Restore from latest backup
        success = restore_latest_backup(str(self.test_file), self.temp_dir)
        
        assert success is True
        
        # Should restore from newest backup
        with open(self.test_file, 'r') as f:
            content = f.read()
        assert content == "new content"
    
    def test_restore_latest_backup_no_backups(self):
        """Test restoration when no backups exist"""
        success = restore_latest_backup(str(self.test_file), self.temp_dir)
        assert success is False
    
    def test_get_backup_stats_empty(self):
        """Test backup statistics with no backups"""
        stats = get_backup_stats(self.temp_dir)
        assert stats["total_backups"] == 0
        assert stats["total_size"] == 0
        assert stats["files_with_backups"] == 0
        assert stats["oldest_backup"] is None
        assert stats["newest_backup"] is None
    
    def test_get_backup_stats_with_backups(self):
        """Test backup statistics with existing backups"""
        # Create backup files
        backup_dir = get_backup_dir(self.temp_dir)
        backup_dir.mkdir(exist_ok=True)
        
        (backup_dir / "test.py.20250613_120000.bak").write_text("content1")
        (backup_dir / "test.py.20250613_130000.bak").write_text("content2")
        (backup_dir / "other.py.20250613_140000.bak").write_text("content3")
        
        stats = get_backup_stats(self.temp_dir)
        assert stats["total_backups"] == 3
        assert stats["total_size"] > 0
        assert stats["files_with_backups"] == 2
        assert "test.py" in stats["backup_files"]
        assert "other.py" in stats["backup_files"]
    
    def test_cleanup_old_backups(self):
        """Test cleanup of old backups"""
        # Create multiple backups
        backup_dir = get_backup_dir(self.temp_dir)
        backup_dir.mkdir(exist_ok=True)
        
        for i in range(10):
            timestamp = f"20250613_{120000 + i:06d}"
            (backup_dir / f"test.py.{timestamp}.bak").touch()
        
        # Clean up old backups (keep 5)
        deleted_count = cleanup_old_backups("test.py", keep_count=5, project_root=self.temp_dir)
        
        assert deleted_count == 5
        
        # Check remaining backups
        remaining_backups = list_backups("test.py", self.temp_dir)
        assert len(remaining_backups) == 5
    
    def test_cleanup_old_backups_not_enough(self):
        """Test cleanup when there aren't enough backups to clean"""
        # Create only 3 backups
        backup_dir = get_backup_dir(self.temp_dir)
        backup_dir.mkdir(exist_ok=True)
        
        for i in range(3):
            timestamp = f"20250613_{120000 + i:06d}"
            (backup_dir / f"test.py.{timestamp}.bak").touch()
        
        # Try to clean up (keep 5, but only 3 exist)
        deleted_count = cleanup_old_backups("test.py", keep_count=5, project_root=self.temp_dir)
        
        assert deleted_count == 0
        
        # All backups should remain
        remaining_backups = list_backups("test.py", self.temp_dir)
        assert len(remaining_backups) == 3
    
    def test_delete_backup(self):
        """Test deletion of specific backup"""
        # Create backup
        backup_path = create_backup(str(self.test_file), self.temp_dir)
        backup_filename = Path(backup_path).name
        
        # Delete backup
        from engine.backup_engine import delete_backup
        success = delete_backup(backup_filename, self.temp_dir)
        
        assert success is True
        
        # Check backup was deleted
        assert not Path(backup_path).exists()
    
    def test_delete_backup_not_found(self):
        """Test deletion of non-existent backup"""
        from engine.backup_engine import delete_backup
        success = delete_backup("nonexistent.bak", self.temp_dir)
        assert success is False
    
    def test_backup_metadata_saved(self):
        """Test that backup metadata is saved"""
        backup_path = create_backup(str(self.test_file), self.temp_dir)
        backup_dir = get_backup_dir(self.temp_dir)
        metadata_file = backup_dir / "backup_metadata.json"
        
        assert metadata_file.exists()
        
        # Check metadata content
        import json
        with open(metadata_file, 'r') as f:
            metadata_list = json.load(f)
        
        assert len(metadata_list) > 0
        latest_metadata = metadata_list[-1]
        assert latest_metadata["original_file"] == str(self.test_file)
        assert latest_metadata["backup_file"] == Path(backup_path).name
        assert "timestamp" in latest_metadata
        assert "created_at" in latest_metadata


class TestBackupEngineIntegration:
    """Integration tests for backup engine"""
    
    def test_full_backup_restore_workflow(self):
        """Test complete backup and restore workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            
            # Create initial file
            with open(test_file, 'w') as f:
                f.write("def hello():\n    print('Hello')\n")
            
            # Create backup
            backup_path = create_backup(str(test_file), temp_dir)
            assert Path(backup_path).exists()
            
            # Modify file
            with open(test_file, 'w') as f:
                f.write("def hello():\n    print('Modified')\n")
            
            # Restore from backup
            backup_filename = Path(backup_path).name
            success = restore_backup(str(test_file), backup_filename, temp_dir)
            assert success is True
            
            # Verify restoration
            with open(test_file, 'r') as f:
                content = f.read()
            assert "print('Hello')" in content
            assert "print('Modified')" not in content
    
    def test_multiple_backups_restore_latest(self):
        """Test restoring from latest backup when multiple exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            
            # Create initial file
            with open(test_file, 'w') as f:
                f.write("version1")
            
            # Create multiple backups
            backup_dir = get_backup_dir(temp_dir)
            backup_dir.mkdir(exist_ok=True)
            
            (backup_dir / "test.py.20250613_120000.bak").write_text("version1")
            (backup_dir / "test.py.20250613_130000.bak").write_text("version2")
            (backup_dir / "test.py.20250613_140000.bak").write_text("version3")
            
            # Modify file
            with open(test_file, 'w') as f:
                f.write("current")
            
            # Restore latest
            success = restore_latest_backup(str(test_file), temp_dir)
            assert success is True
            
            # Should restore version3 (latest)
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == "version3" 