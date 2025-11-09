"""
Director Agent Router - LangGraph-based video creation workflow
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
import os
import logging
from pathlib import Path
import uuid
import shutil
from datetime import datetime, timezone

# Import Director workflow
import sys
sys.path.append(str(Path(__file__).parent.parent / "agents"))
from director_workflow import DirectorWorkflow, DirectorState
from viral_formats import seed_viral_formats
from langchain_core.messages import HumanMessage


logger = logging.getLogger(__name__)
router = APIRouter()


# Get database connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


# Pydantic models
class DirectorProjectCreate(BaseModel):
    user_goal: str
    product_type: Optional[str] = "general"
    target_platform: Optional[str] = "YouTube"


class DirectorMessageInput(BaseModel):
    project_id: str
    message: str


class DirectorResponse(BaseModel):
    project_id: str
    message: str
    current_step: str
    shot_list: Optional[List[Dict[str, Any]]] = None
    matched_format: Optional[Dict[str, Any]] = None
    user_input_needed: bool = False
    next_instruction: str = ""


@router.post("/project", response_model=DirectorResponse)
async def create_director_project(input: DirectorProjectCreate):
    """Create a new video project with the Director workflow"""
    try:
        project_id = str(uuid.uuid4())
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        
        if not api_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        # Initialize Director workflow
        workflow = DirectorWorkflow(db=db, api_key=api_key)
        
        # Create initial state
        initial_state: DirectorState = {
            "messages": [HumanMessage(content=input.user_goal)],
            "project_id": project_id,
            "user_goal": input.user_goal,
            "product_type": input.product_type,
            "target_platform": input.target_platform,
            "matched_format": None,
            "shot_list": None,
            "uploaded_segments": [],
            "edited_video_path": None,
            "current_step": "initial",
            "user_input_needed": False,
            "next_instruction": ""
        }
        
        # Run the workflow
        result = await workflow.graph.ainvoke(initial_state)
        
        # Extract latest AI message
        ai_messages = [m for m in result["messages"] if hasattr(m, 'content')]
        latest_message = ai_messages[-1].content if ai_messages else "Project created successfully!"
        
        return DirectorResponse(
            project_id=project_id,
            message=latest_message,
            current_step=result.get("current_step", "initial"),
            shot_list=result.get("shot_list"),
            matched_format=result.get("matched_format"),
            user_input_needed=result.get("user_input_needed", False),
            next_instruction=result.get("next_instruction", "")
        )
    except Exception as e:
        logger.error(f"Error creating director project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=DirectorResponse)
async def send_director_message(
    input: DirectorMessageInput,
    current_user: UserResponse = Depends(get_current_user)
):
    """Send a message in an existing Director project"""
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        
        if not api_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        # Load project state from database - verify ownership
        project = await db.video_projects.find_one({
            "project_id": input.project_id,
            "user_id": current_user.id
        }, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Initialize workflow
        workflow = DirectorWorkflow(db=db, api_key=api_key)
        
        # Reconstruct messages from database
        stored_messages = project.get("messages", [])
        messages = []
        for msg in stored_messages:
            if msg.get("type") == "human":
                messages.append(HumanMessage(content=msg.get("content", "")))
        
        # Add new message
        messages.append(HumanMessage(content=input.message))
        
        # Reconstruct state from project data
        state: DirectorState = {
            "messages": messages,
            "project_id": input.project_id,
            "user_goal": project.get("user_goal", ""),
            "product_type": project.get("product_type", "general"),
            "target_platform": project.get("target_platform", "YouTube"),
            "matched_format": project.get("matched_format"),
            "shot_list": project.get("shot_list"),
            "uploaded_segments": project.get("uploaded_segments", []),
            "edited_video_path": project.get("edited_video_path"),
            "current_step": project.get("current_step", "initial"),
            "user_input_needed": False,
            "next_instruction": ""
        }
        
        # Run workflow
        result = await workflow.graph.ainvoke(state)
        
        # Extract latest AI message
        ai_messages = [m for m in result["messages"] if hasattr(m, 'content')]
        latest_message = ai_messages[-1].content if ai_messages else "Processing..."
        
        return DirectorResponse(
            project_id=input.project_id,
            message=latest_message,
            current_step=result.get("current_step", "initial"),
            shot_list=result.get("shot_list"),
            matched_format=result.get("matched_format"),
            user_input_needed=result.get("user_input_needed", False),
            next_instruction=result.get("next_instruction", "")
        )
    except Exception as e:
        logger.error(f"Error processing director message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-segment")
async def upload_video_segment(
    project_id: str,
    segment_name: str,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    """Upload a video segment for a project (replaces existing if present)"""
    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path("/app/backend/uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Get project and verify ownership
        project = await db.video_projects.find_one({
            "project_id": project_id,
            "user_id": current_user.id
        }, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Delete old file if it exists for this segment
        if project and project.get("uploaded_segments"):
            for seg in project["uploaded_segments"]:
                if seg.get("segment_name") == segment_name:
                    old_file_path = Path(seg.get("file_path", ""))
                    if old_file_path.exists():
                        try:
                            old_file_path.unlink()
                            logger.info(f"Deleted old file for segment {segment_name}: {old_file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete old file {old_file_path}: {e}")
        
        # Save new file
        file_path = upload_dir / f"{project_id}_{segment_name}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update project in database - remove old segment and add new one
        segment_data = {
            "segment_name": segment_name,
            "file_path": str(file_path),
            "filename": file.filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Remove any existing segment with same name, then add the new one
        await db.video_projects.update_one(
            {"project_id": project_id},
            {
                "$pull": {"uploaded_segments": {"segment_name": segment_name}}
            }
        )
        
        await db.video_projects.update_one(
            {"project_id": project_id},
            {
                "$push": {"uploaded_segments": segment_data},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        # Update shot list to mark segment as uploaded
        project = await db.video_projects.find_one({"project_id": project_id}, {"_id": 0})
        if project and project.get("shot_list"):
            shot_list = project["shot_list"]
            for shot in shot_list:
                if shot.get("segment_name") == segment_name:
                    shot["uploaded"] = True
            
            await db.video_projects.update_one(
                {"project_id": project_id},
                {"$set": {"shot_list": shot_list}}
            )
        
        return {
            "success": True,
            "message": f"Segment '{segment_name}' uploaded successfully",
            "file_path": str(file_path)
        }
    except Exception as e:
        logger.error(f"Error uploading segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}")
async def get_director_project(
    project_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get project details - returns user's own projects or migrates old projects"""
    # Try to find project with user_id
    project = await db.video_projects.find_one({
        "project_id": project_id,
        "user_id": current_user.id
    }, {"_id": 0})
    
    # If not found, check for old project without user_id (migration)
    if not project:
        old_project = await db.video_projects.find_one({
            "project_id": project_id,
            "user_id": {"$exists": False}
        }, {"_id": 0})
        
        if old_project:
            # Migrate: add current user as owner
            await db.video_projects.update_one(
                {"project_id": project_id},
                {"$set": {"user_id": current_user.id}}
            )
            old_project["user_id"] = current_user.id
            logger.info(f"Migrated project {project_id} to user {current_user.id}")
            return old_project
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    return project


@router.post("/seed-formats")
async def seed_formats():
    """Seed viral formats database (admin endpoint)"""
    try:
        await seed_viral_formats(db)
        return {"success": True, "message": "Viral formats seeded successfully"}
    except Exception as e:
        logger.error(f"Error seeding formats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Video Assembly Endpoints
from services.video_assembly_service import VideoAssemblyService

# Create assembly service instance
assembly_service = VideoAssemblyService(db)


class AssemblyOptions(BaseModel):
    add_transitions: bool = True
    transition_type: str = Field(default="fade", description="fade, wipe, dissolve, slidedown, slideup")
    transition_duration: float = 0.8
    add_subtitles: bool = True
    subtitle_position: str = Field(default="bottom", description="top, center, bottom")
    subtitle_font_size: int = 48
    optimize_platform: Optional[str] = Field(default="youtube", description="tiktok, instagram, youtube")


class AssembleVideoRequest(BaseModel):
    project_id: str
    options: Optional[AssemblyOptions] = None


@router.post("/assemble")
async def assemble_project_video(request: AssembleVideoRequest):
    """
    Assemble all project segments into final video with transitions and effects
    
    This endpoint:
    1. Collects all uploaded segments for the project
    2. Adds subtitles from shot scripts (if enabled)
    3. Merges segments with transitions
    4. Optimizes for target platform
    """
    try:
        project_id = request.project_id
        
        # Get project details
        project = await db.video_projects.find_one({"project_id": project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get shot list
        shot_list = project.get("shot_list", [])
        if not shot_list:
            raise HTTPException(status_code=400, detail="Project has no shot list")
        
        # Get uploaded segments
        segment_paths = await assembly_service.get_project_segments(project_id)
        
        if not segment_paths:
            raise HTTPException(
                status_code=400, 
                detail="No video segments found. Please upload segments first."
            )
        
        logger.info(f"Starting assembly for project {project_id} with {len(segment_paths)} segments")
        
        # Convert options to dict
        options_dict = request.options.model_dump() if request.options else {}
        
        # Start assembly
        assembly_id = await assembly_service.start_assembly(
            project_id=project_id,
            segment_paths=segment_paths,
            shot_list=shot_list,
            options=options_dict
        )
        
        return {
            "success": True,
            "assembly_id": assembly_id,
            "message": f"Video assembly started. Processing {len(segment_paths)} segments.",
            "segments_count": len(segment_paths)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting video assembly: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Shot Management Endpoints

class ShotUpdate(BaseModel):
    project_id: str
    shot_index: int
    segment_name: Optional[str] = None
    script: Optional[str] = None
    visual_guide: Optional[str] = None
    duration: Optional[int] = None


class ShotAdd(BaseModel):
    project_id: str
    segment_name: str
    script: str
    visual_guide: str
    duration: int = 15


class ShotDelete(BaseModel):
    project_id: str
    shot_index: int


class ShotReorder(BaseModel):
    project_id: str
    shot_list: List[Dict[str, Any]]


@router.put("/shot/update")
async def update_shot(input: ShotUpdate):
    """Update an existing shot in the shot list"""
    try:
        project = await db.video_projects.find_one({"project_id": input.project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get shot list
        shot_list = project.get("shot_list", [])
        
        if input.shot_index < 0 or input.shot_index >= len(shot_list):
            raise HTTPException(status_code=400, detail="Invalid shot index")
        
        # Update shot fields
        shot = shot_list[input.shot_index]
        if input.segment_name is not None:
            shot["segment_name"] = input.segment_name
        if input.script is not None:
            shot["script"] = input.script
        if input.visual_guide is not None:
            shot["visual_guide"] = input.visual_guide
        if input.duration is not None:
            shot["duration"] = input.duration
        
        # Save to database
        await db.video_projects.update_one(
            {"project_id": input.project_id},
            {
                "$set": {
                    "shot_list": shot_list,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "shot_list": shot_list,
            "message": "Shot updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating shot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assembly-status/{assembly_id}")
async def get_assembly_status(assembly_id: str):
    """
    Get status of video assembly job
    
    Returns progress, status, and output path when complete
    """
    try:
        status = await assembly_service.get_assembly_status(assembly_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Assembly job not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assembly status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{assembly_id}")
async def download_assembled_video(assembly_id: str):
    """
    Download the assembled video file
    """
    from fastapi.responses import FileResponse
    
    try:
        status = await assembly_service.get_assembly_status(assembly_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Assembly job not found")
        
        if status['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Assembly not complete. Status: {status['status']}"
            )
        
        output_path = status['output_path']
        
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Get filename from path
        filename = Path(output_path).name
        
        return FileResponse(
            path=output_path,
            media_type="video/mp4",
            filename=f"assembled_{filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shot/add")
async def add_shot(input: ShotAdd):
    """Add a new shot to the shot list"""
    try:
        project = await db.video_projects.find_one({"project_id": input.project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        shot_list = project.get("shot_list", [])
        
        # Create new shot
        new_shot = {
            "segment_name": input.segment_name,
            "script": input.script,
            "visual_guide": input.visual_guide,
            "duration": input.duration,
            "uploaded": False,
            "required": False  # All shots are now optional
        }
        
        shot_list.append(new_shot)
        
        # Save to database
        await db.video_projects.update_one(
            {"project_id": input.project_id},
            {
                "$set": {
                    "shot_list": shot_list,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Shot added successfully",
            "shot_list": shot_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding shot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shot/delete")
async def delete_shot(input: ShotDelete):
    """Delete a shot from the shot list"""
    try:
        project = await db.video_projects.find_one({"project_id": input.project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        shot_list = project.get("shot_list", [])
        
        if input.shot_index < 0 or input.shot_index >= len(shot_list):
            raise HTTPException(status_code=400, detail="Invalid shot index")
        
        # Remove shot
        deleted_shot = shot_list.pop(input.shot_index)
        
        # Save to database
        await db.video_projects.update_one(
            {"project_id": input.project_id},
            {
                "$set": {
                    "shot_list": shot_list,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": f"Shot '{deleted_shot.get('segment_name')}' deleted successfully",
            "shot_list": shot_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/shot/reorder")
async def reorder_shots(input: ShotReorder):
    """Reorder the shot list"""
    try:
        project = await db.video_projects.find_one({"project_id": input.project_id}, {"_id": 0})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Save reordered shot list to database
        await db.video_projects.update_one(
            {"project_id": input.project_id},
            {
                "$set": {
                    "shot_list": input.shot_list,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Shot list reordered successfully",
            "shot_list": input.shot_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering shots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
