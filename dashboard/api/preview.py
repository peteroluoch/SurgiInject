"""
Preview API endpoints for SurgiInject dashboard
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add the parent directory to the path to import engine modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.diff_engine import preview_injection, batch_preview_injection, get_diff_stats

router = APIRouter()


class InjectionPreviewRequest(BaseModel):
    file_path: str
    prompt_path: str
    with_context: bool = True
    project_root: Optional[str] = None


class BatchPreviewRequest(BaseModel):
    files: List[str]
    prompt_path: str
    with_context: bool = True
    project_root: Optional[str] = None


class DiffStatsRequest(BaseModel):
    diff: str


@router.post("/preview")
async def preview_injection_endpoint(request: InjectionPreviewRequest):
    """
    Preview injection for a single file
    """
    try:
        result = preview_injection(
            file_path=request.file_path,
            prompt_path=request.prompt_path,
            with_context=request.with_context,
            project_root=request.project_root
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Add diff stats
        if result.get("diff"):
            stats = get_diff_stats(result["diff"])
            result["diff_stats"] = stats
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/batch-preview")
async def batch_preview_endpoint(request: BatchPreviewRequest):
    """
    Preview injection for multiple files
    """
    try:
        result = batch_preview_injection(
            files=request.files,
            prompt_path=request.prompt_path,
            with_context=request.with_context,
            project_root=request.project_root
        )
        
        # Add diff stats for each preview
        for preview in result["previews"]:
            if preview.get("diff"):
                stats = get_diff_stats(preview["diff"])
                preview["diff_stats"] = stats
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch preview failed: {str(e)}")


@router.post("/diff-stats")
async def get_diff_stats_endpoint(request: DiffStatsRequest):
    """
    Get statistics for a diff
    """
    try:
        stats = get_diff_stats(request.diff)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze diff: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "preview-api"} 