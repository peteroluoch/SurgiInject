"""
Apply API endpoints for SurgiInject dashboard
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add the parent directory to the path to import engine modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.diff_engine import apply_injection

router = APIRouter()


class ApplyRequest(BaseModel):
    file_path: str
    injected_content: str


class BatchApplyRequest(BaseModel):
    applications: List[ApplyRequest]


class ApplyResponse(BaseModel):
    success: bool
    filename: str
    backup_created: Optional[bool] = None
    backup_path: Optional[str] = None
    error: Optional[str] = None


@router.post("/apply")
async def apply_injection_endpoint(request: ApplyRequest):
    """
    Apply injection to a single file
    """
    try:
        result = apply_injection(
            file_path=request.file_path,
            injected_content=request.injected_content
        )
        
        return ApplyResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply failed: {str(e)}")


@router.post("/batch-apply")
async def batch_apply_endpoint(request: BatchApplyRequest):
    """
    Apply injection to multiple files
    """
    results = []
    
    for application in request.applications:
        try:
            result = apply_injection(
                file_path=application.file_path,
                injected_content=application.injected_content
            )
            results.append(ApplyResponse(**result))
        except Exception as e:
            results.append(ApplyResponse(
                success=False,
                filename=application.file_path,
                error=str(e)
            ))
    
    return {
        "results": results,
        "total_files": len(results),
        "successful_applications": len([r for r in results if r.success]),
        "failed_applications": len([r for r in results if not r.success])
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "apply-api"} 