"""
Undo API endpoints for SurgiInject dashboard
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add the parent directory to the path to import engine modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.backup_engine import (
    list_backups, 
    restore_backup, 
    restore_latest_backup, 
    get_backup_stats,
    cleanup_old_backups
)

router = APIRouter()


class UndoRequest(BaseModel):
    file_path: str
    backup_file: Optional[str] = None


class BackupListRequest(BaseModel):
    file_path: str


class CleanupRequest(BaseModel):
    file_path: Optional[str] = None
    keep_count: int = 5


@router.post("/undo")
async def undo_injection(request: UndoRequest):
    """
    Undo injection by restoring from backup
    """
    try:
        if request.backup_file:
            # Restore from specific backup
            success = restore_backup(request.file_path, request.backup_file)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to restore from {request.backup_file}")
            
            return {
                "success": True,
                "message": f"File restored from {request.backup_file}",
                "restored_file": request.file_path,
                "backup_used": request.backup_file
            }
        else:
            # Restore from latest backup
            success = restore_latest_backup(request.file_path)
            if not success:
                raise HTTPException(status_code=400, detail="No backup found or restore failed")
            
            return {
                "success": True,
                "message": "File restored from latest backup",
                "restored_file": request.file_path
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Undo failed: {str(e)}")


@router.post("/list-backups")
async def list_file_backups(request: BackupListRequest):
    """
    List available backups for a file
    """
    try:
        from pathlib import Path
        file_path = Path(request.file_path)
        backups = list_backups(file_path.name)
        
        return {
            "file": request.file_path,
            "backups": backups,
            "count": len(backups)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.get("/backup-stats")
async def get_backup_statistics():
    """
    Get backup statistics
    """
    try:
        stats = get_backup_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup stats: {str(e)}")


@router.post("/cleanup")
async def cleanup_backups(request: CleanupRequest):
    """
    Clean up old backups
    """
    try:
        if request.file_path:
            # Clean up backups for specific file
            from pathlib import Path
            file_name = Path(request.file_path).name
            deleted_count = cleanup_old_backups(file_name, request.keep_count)
            
            return {
                "success": True,
                "message": f"Cleaned up {deleted_count} old backups for {file_name}",
                "deleted_count": deleted_count,
                "file": request.file_path
            }
        else:
            # Clean up all backups
            stats = get_backup_stats()
            total_deleted = 0
            
            for backup_file in stats.get('backup_files', []):
                deleted_count = cleanup_old_backups(backup_file, request.keep_count)
                total_deleted += deleted_count
            
            return {
                "success": True,
                "message": f"Cleaned up {total_deleted} old backups total",
                "deleted_count": total_deleted
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "undo-api"} 