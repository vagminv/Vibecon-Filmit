"""
Video Assembly Service - Assembles Director shot segments into final video using ffmpeg
"""

import asyncio
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import ffmpeg tools
import sys
sys.path.append(str(Path(__file__).parent.parent / "agents"))
from video_tools import (
    ffmpeg_merge_videos,
    ffmpeg_add_transition,
    ffmpeg_add_subtitles,
    get_video_metadata,
    optimize_for_platform,
    PROCESSED_DIR,
    UPLOAD_DIR
)

logger = logging.getLogger(__name__)


# Check FFmpeg availability at module load
def check_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible"""
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')
    
    if not ffmpeg_path or not ffprobe_path:
        logger.error("=" * 60)
        logger.error("FFmpeg is not installed or not found in PATH!")
        logger.error("Please install FFmpeg to use video assembly features.")
        logger.error("Run: apt-get update && apt-get install -y ffmpeg")
        logger.error("Or run the setup script: /app/setup.sh")
        logger.error("=" * 60)
        return False
    
    logger.info(f"FFmpeg found at: {ffmpeg_path}")
    logger.info(f"FFprobe found at: {ffprobe_path}")
    return True


# Store FFmpeg availability status
FFMPEG_AVAILABLE = check_ffmpeg_installed()


class VideoAssemblyOptions(Dict):
    """Options for video assembly"""
    add_transitions: bool = True
    transition_type: str = "fade"  # fade, wipe, dissolve, slidedown, slideup
    transition_duration: float = 0.5
    add_subtitles: bool = False
    subtitle_position: str = "bottom"
    subtitle_font_size: int = 48
    optimize_platform: Optional[str] = None  # tiktok, instagram, youtube
    add_intro: bool = False
    add_outro: bool = False


class VideoAssemblyService:
    """Service for assembling video segments into final video"""
    
    def __init__(self, db):
        self.db = db
        self.assembly_jobs = {}  # In-memory tracking for MVP
        
    async def start_assembly(
        self, 
        project_id: str, 
        segment_paths: List[str],
        shot_list: List[Dict[str, Any]],
        options: Dict[str, Any] = None
    ) -> str:
        """
        Start video assembly process (replaces existing assembly if present)
        
        Args:
            project_id: Director project ID
            segment_paths: List of video file paths to assemble
            shot_list: Shot list with scripts for subtitles
            options: Assembly options (transitions, subtitles, etc.)
            
        Returns:
            assembly_id for tracking progress
        """
        assembly_id = str(uuid.uuid4())
        
        # Clean up old assembly files for this project
        try:
            old_assemblies = await self.db.video_assemblies.find(
                {"project_id": project_id}
            ).to_list(length=100)
            
            for old_assembly in old_assemblies:
                # Delete old assembled video files
                if old_assembly.get('output_path'):
                    old_file = Path(old_assembly['output_path'])
                    if old_file.exists():
                        try:
                            old_file.unlink()
                            logger.info(f"Deleted old assembly file: {old_file}")
                        except Exception as e:
                            logger.warning(f"Could not delete old assembly file {old_file}: {e}")
                
                # Delete temporary files for this assembly
                old_id = old_assembly.get('assembly_id', '')
                if old_id:
                    temp_files = list(Path(PROCESSED_DIR).glob(f"{old_id}_*"))
                    for temp_file in temp_files:
                        try:
                            temp_file.unlink()
                            logger.info(f"Deleted temp file: {temp_file}")
                        except Exception as e:
                            logger.warning(f"Could not delete temp file {temp_file}: {e}")
            
            # Delete old assembly records from database
            if old_assemblies:
                await self.db.video_assemblies.delete_many({"project_id": project_id})
                logger.info(f"Deleted {len(old_assemblies)} old assembly records for project {project_id}")
                
        except Exception as e:
            logger.warning(f"Error cleaning up old assemblies: {e}")
        
        # Set default options
        if options is None:
            options = {}
        
        options.setdefault('add_transitions', True)
        options.setdefault('transition_type', 'fade')
        options.setdefault('transition_duration', 0.8)
        options.setdefault('add_subtitles', True)
        options.setdefault('subtitle_position', 'bottom')
        options.setdefault('subtitle_font_size', 48)
        options.setdefault('optimize_platform', 'youtube')
        
        # Create assembly job
        job = {
            'assembly_id': assembly_id,
            'project_id': project_id,
            'status': 'queued',
            'progress': 0,
            'segment_paths': segment_paths,
            'shot_list': shot_list,
            'options': options,
            'created_at': datetime.now().isoformat(),
            'output_path': None,
            'error': None
        }
        
        self.assembly_jobs[assembly_id] = job
        
        # Start assembly in background
        asyncio.create_task(self._assemble_video(assembly_id))
        
        logger.info(f"Started assembly job {assembly_id} for project {project_id}")
        
        return assembly_id
    
    async def _assemble_video(self, assembly_id: str):
        """Background task to assemble video"""
        job = self.assembly_jobs[assembly_id]
        
        try:
            job['status'] = 'processing'
            job['progress'] = 10
            
            segment_paths = job['segment_paths']
            shot_list = job['shot_list']
            options = job['options']
            
            logger.info(f"Assembly {assembly_id}: Processing {len(segment_paths)} segments")
            
            # Step 1: Add subtitles to each segment if enabled
            processed_segments = []
            
            if options['add_subtitles'] and shot_list:
                job['progress'] = 20
                logger.info(f"Assembly {assembly_id}: Adding subtitles")
                
                for i, (segment_path, shot) in enumerate(zip(segment_paths, shot_list)):
                    if not os.path.exists(segment_path):
                        logger.warning(f"Segment not found: {segment_path}")
                        continue
                    
                    script = shot.get('script', '')
                    if script:
                        # Add subtitles
                        output_name = f"{assembly_id}_subtitle_{i}.mp4"
                        result = await ffmpeg_add_subtitles(
                            input_file=segment_path,
                            output_file=output_name,
                            subtitle_text=script[:100],  # Limit length for MVP
                            font_size=options['subtitle_font_size'],
                            position=options['subtitle_position']
                        )
                        
                        if result['success']:
                            processed_segments.append(result['output_file'])
                            logger.info(f"Added subtitles to segment {i}")
                        else:
                            # Use original if subtitle fails
                            processed_segments.append(segment_path)
                            logger.warning(f"Subtitle failed for segment {i}: {result.get('error')}")
                    else:
                        processed_segments.append(segment_path)
            else:
                processed_segments = segment_paths
            
            job['progress'] = 40
            
            # Step 2: Merge segments with transitions
            if options['add_transitions'] and len(processed_segments) > 1:
                logger.info(f"Assembly {assembly_id}: Adding transitions")
                job['progress'] = 50
                
                merged_output = await self._merge_with_transitions(
                    assembly_id,
                    processed_segments,
                    options['transition_type'],
                    options['transition_duration']
                )
            else:
                # Simple concatenation without transitions
                logger.info(f"Assembly {assembly_id}: Simple merge")
                job['progress'] = 50
                
                output_name = f"{assembly_id}_merged.mp4"
                result = await ffmpeg_merge_videos(
                    input_files=processed_segments,
                    output_file=output_name,
                    transition_duration=0
                )
                
                if not result['success']:
                    raise Exception(f"Merge failed: {result.get('error')}")
                
                merged_output = result['output_file']
            
            job['progress'] = 70
            
            # Step 3: Optimize for platform if specified
            final_output = merged_output
            
            if options.get('optimize_platform'):
                logger.info(f"Assembly {assembly_id}: Optimizing for {options['optimize_platform']}")
                job['progress'] = 80
                
                optimized_name = f"{assembly_id}_final.mp4"
                result = await optimize_for_platform(
                    input_file=merged_output,
                    output_file=optimized_name,
                    platform=options['optimize_platform']
                )
                
                if result['success']:
                    final_output = result['output_file']
                    logger.info(f"Optimized for {options['optimize_platform']}")
                else:
                    logger.warning(f"Optimization failed: {result.get('error')}")
            
            job['progress'] = 90
            
            # Get final video metadata
            metadata = await get_video_metadata(final_output)
            
            # Update job with success
            job['status'] = 'completed'
            job['progress'] = 100
            job['output_path'] = final_output
            job['metadata'] = metadata
            job['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"Assembly {assembly_id}: Completed successfully")
            
            # Save to database
            await self.db.video_assemblies.insert_one({
                **job,
                '_id': assembly_id
            })
            
        except Exception as e:
            logger.error(f"Assembly {assembly_id} failed: {str(e)}")
            job['status'] = 'failed'
            job['error'] = str(e)
            job['failed_at'] = datetime.now().isoformat()
    
    async def _merge_with_transitions(
        self,
        assembly_id: str,
        segments: List[str],
        transition_type: str,
        transition_duration: float
    ) -> str:
        """
        Merge segments with transitions between them
        
        For MVP: Use xfade filter to add transitions
        """
        if len(segments) == 1:
            return segments[0]
        
        # Build complex filter for all segments with transitions
        # For simplicity in MVP, merge pairs with transitions
        
        current_output = segments[0]
        
        for i in range(1, len(segments)):
            temp_output = f"{assembly_id}_transition_{i}.mp4"
            
            result = await ffmpeg_add_transition(
                video1=current_output,
                video2=segments[i],
                output_file=temp_output,
                transition_type=transition_type,
                duration=transition_duration
            )
            
            if not result['success']:
                logger.warning(f"Transition {i} failed: {result.get('error')}")
                # Fall back to simple concat
                result = await ffmpeg_merge_videos(
                    input_files=[current_output, segments[i]],
                    output_file=temp_output,
                    transition_duration=0
                )
                
                if not result['success']:
                    raise Exception(f"Merge failed: {result.get('error')}")
            
            current_output = result['output_file']
        
        return current_output
    
    async def get_assembly_status(self, assembly_id: str) -> Dict[str, Any]:
        """Get status of assembly job"""
        job = self.assembly_jobs.get(assembly_id)
        
        if not job:
            # Check database
            db_job = await self.db.video_assemblies.find_one({'_id': assembly_id})
            if db_job:
                return {
                    'assembly_id': assembly_id,
                    'status': db_job['status'],
                    'progress': db_job.get('progress', 100),
                    'output_path': db_job.get('output_path'),
                    'metadata': db_job.get('metadata'),
                    'error': db_job.get('error'),
                    'created_at': db_job.get('created_at'),
                    'completed_at': db_job.get('completed_at')
                }
            return None
        
        return {
            'assembly_id': assembly_id,
            'status': job['status'],
            'progress': job['progress'],
            'output_path': job.get('output_path'),
            'metadata': job.get('metadata'),
            'error': job.get('error'),
            'created_at': job['created_at'],
            'completed_at': job.get('completed_at')
        }
    
    async def get_project_segments(self, project_id: str) -> List[str]:
        """
        Get list of uploaded segment file paths for a project
        
        Looks in /app/backend/uploads/ for files matching project_id pattern
        """
        upload_dir = Path(UPLOAD_DIR)
        segment_files = []
        
        # Find all files for this project
        for file_path in upload_dir.glob(f"{project_id}_*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
                segment_files.append(str(file_path))
        
        # Sort by segment name to maintain order
        segment_files.sort()
        
        logger.info(f"Found {len(segment_files)} segments for project {project_id}")
        
        return segment_files
