"""
Backup Engine for SurgiInject
Provides automatic backup and restoration capabilities
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Backup directory relative to project root
BACKUP_DIR = ".surgi_backups"
BACKUP_METADATA_FILE = "backup_metadata.json"


def get_backup_dir(project_root: Optional[str] = None) -> Path:
    """
    Get the backup directory path.
    
    Args:
        project_root: Optional project root directory
        
    Returns:
        Path to backup directory
    """
    if project_root:
        return Path(project_root) / BACKUP_DIR
    else:
        # Default to current working directory
        return Path.cwd() / BACKUP_DIR


def ensure_backup_dir(backup_dir: Path) -> None:
    """
    Ensure backup directory exists.
    
    Args:
        backup_dir: Path to backup directory
    """
    backup_dir.mkdir(exist_ok=True)
    logger.info(f"Backup directory ensured: {backup_dir}")


def create_backup(file_path: str, project_root: Optional[str] = None) -> str:
    """
    Create a backup of a file before modification.
    
    Args:
        file_path: Path to the file to backup
        project_root: Optional project root directory
        
    Returns:
        Path to the created backup file
    """
    file_path = Path(file_path)
    backup_dir = get_backup_dir(project_root)
    ensure_backup_dir(backup_dir)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{file_path.name}.{timestamp}.bak"
    backup_path = backup_dir / backup_filename
    
    try:
        # Copy the file
        shutil.copy2(file_path, backup_path)
        
        # Create metadata entry
        metadata = {
            "original_file": str(file_path),
            "backup_file": backup_filename,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "file_size": file_path.stat().st_size,
            "checksum": None  # Could add checksum verification later
        }
        
        # Save metadata
        save_backup_metadata(backup_dir, metadata)
        
        logger.info(f"Backup created: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {e}")
        raise


def list_backups(file_basename: str, project_root: Optional[str] = None) -> List[str]:
    """
    List all backups for a specific file.
    
    Args:
        file_basename: Base name of the file (e.g., "utils.py")
        project_root: Optional project root directory
        
    Returns:
        List of backup filenames, sorted by timestamp (newest first)
    """
    backup_dir = get_backup_dir(project_root)
    
    if not backup_dir.exists():
        return []
    
    # Find all backup files for this file
    backup_files = []
    for backup_file in backup_dir.glob(f"{file_basename}.*.bak"):
        backup_files.append(backup_file.name)
    
    # Sort by timestamp (newest first)
    backup_files.sort(reverse=True)
    return backup_files


def get_backup_info(backup_filename: str, project_root: Optional[str] = None) -> Optional[Dict]:
    """
    Get information about a specific backup.
    
    Args:
        backup_filename: Name of the backup file
        project_root: Optional project root directory
        
    Returns:
        Dictionary with backup metadata or None if not found
    """
    backup_dir = get_backup_dir(project_root)
    metadata_file = backup_dir / BACKUP_METADATA_FILE
    
    if not metadata_file.exists():
        return None
    
    try:
        with open(metadata_file, 'r') as f:
            metadata_list = json.load(f)
        
        for metadata in metadata_list:
            if metadata.get("backup_file") == backup_filename:
                return metadata
    except Exception as e:
        logger.error(f"Failed to read backup metadata: {e}")
    
    return None


def restore_backup(file_path: str, backup_filename: str, project_root: Optional[str] = None) -> bool:
    """
    Restore a file from a backup.
    
    Args:
        file_path: Path to the file to restore
        backup_filename: Name of the backup file to restore from
        project_root: Optional project root directory
        
    Returns:
        True if restoration was successful, False otherwise
    """
    file_path = Path(file_path)
    backup_dir = get_backup_dir(project_root)
    backup_path = backup_dir / backup_filename
    
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return False
    
    try:
        # Restore from backup directly
        shutil.copy2(backup_path, file_path)
        logger.info(f"File restored from backup: {file_path} <- {backup_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to restore {file_path} from {backup_filename}: {e}")
        return False


def restore_latest_backup(file_path: str, project_root: Optional[str] = None) -> bool:
    """
    Restore a file from its latest backup.
    
    Args:
        file_path: Path to the file to restore
        project_root: Optional project root directory
        
    Returns:
        True if restoration was successful, False otherwise
    """
    file_basename = Path(file_path).name
    backups = list_backups(file_basename, project_root)
    
    if not backups:
        logger.error(f"No backups found for {file_basename}")
        return False
    
    latest_backup = backups[0]  # First in sorted list (newest first)
    return restore_backup(file_path, latest_backup, project_root)


def delete_backup(backup_filename: str, project_root: Optional[str] = None) -> bool:
    """
    Delete a specific backup file.
    
    Args:
        backup_filename: Name of the backup file to delete
        project_root: Optional project root directory
        
    Returns:
        True if deletion was successful, False otherwise
    """
    backup_dir = get_backup_dir(project_root)
    backup_path = backup_dir / backup_filename
    
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return False
    
    try:
        backup_path.unlink()
        logger.info(f"Backup deleted: {backup_filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete backup {backup_filename}: {e}")
        return False


def cleanup_old_backups(file_basename: str, keep_count: int = 5, project_root: Optional[str] = None) -> int:
    """
    Clean up old backups, keeping only the specified number of recent ones.
    
    Args:
        file_basename: Base name of the file
        keep_count: Number of recent backups to keep
        project_root: Optional project root directory
        
    Returns:
        Number of backups deleted
    """
    backups = list_backups(file_basename, project_root)
    
    if len(backups) <= keep_count:
        return 0
    
    deleted_count = 0
    for backup in backups[keep_count:]:
        if delete_backup(backup, project_root):
            deleted_count += 1
    
    logger.info(f"Cleaned up {deleted_count} old backups for {file_basename}")
    return deleted_count


def save_backup_metadata(backup_dir: Path, metadata: Dict) -> None:
    """
    Save backup metadata to JSON file.
    
    Args:
        backup_dir: Backup directory path
        metadata: Metadata dictionary to save
    """
    metadata_file = backup_dir / BACKUP_METADATA_FILE
    
    try:
        # Load existing metadata
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata_list = json.load(f)
        else:
            metadata_list = []
        
        # Add new metadata
        metadata_list.append(metadata)
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata_list, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save backup metadata: {e}")


def get_backup_stats(project_root: Optional[str] = None) -> Dict:
    """
    Get statistics about backups.
    
    Args:
        project_root: Optional project root directory
        
    Returns:
        Dictionary with backup statistics
    """
    backup_dir = get_backup_dir(project_root)
    
    if not backup_dir.exists():
        return {
            "total_backups": 0,
            "total_size": 0,
            "files_with_backups": 0,
            "oldest_backup": None,
            "newest_backup": None
        }
    
    total_size = 0
    backup_files = list(backup_dir.glob("*.bak"))
    file_groups = {}
    
    for backup_file in backup_files:
        total_size += backup_file.stat().st_size
        
        # Group by original filename
        parts = backup_file.name.split('.')
        if len(parts) >= 3:
            original_name = '.'.join(parts[:-2])  # Remove timestamp and .bak
            if original_name not in file_groups:
                file_groups[original_name] = []
            file_groups[original_name].append(backup_file.name)
    
    # Get oldest and newest timestamps
    timestamps = []
    for backup_file in backup_files:
        parts = backup_file.name.split('.')
        if len(parts) >= 3:
            timestamp_str = parts[-2]  # Get timestamp part
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                timestamps.append(timestamp)
            except ValueError:
                continue
    
    return {
        "total_backups": len(backup_files),
        "total_size": total_size,
        "files_with_backups": len(file_groups),
        "oldest_backup": min(timestamps).isoformat() if timestamps else None,
        "newest_backup": max(timestamps).isoformat() if timestamps else None,
        "backup_files": list(file_groups.keys())
    } 