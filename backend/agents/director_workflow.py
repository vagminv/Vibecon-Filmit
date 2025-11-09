"""
LangGraph Director Workflow - Conversational AI Director with intelligent task delegation.
Handles free-flowing conversations and routes tasks to specialized agents.
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from emergentintegrations.llm.chat import LlmChat, UserMessage
from motor.motor_asyncio import AsyncIOMotorDatabase
import json
from datetime import datetime, timezone

from viral_formats import (
    query_viral_formats, 
    calculate_format_match_score,
    get_format_by_id
)
from video_tools import (
    ffmpeg_merge_videos,
    ffmpeg_cut_video,
    ffmpeg_add_subtitles,
    get_video_metadata,
    optimize_for_platform
)
from feedback_agent import FeedbackAgent, get_overall_project_feedback
from shot_list_manager import ShotListManager, suggest_shot_improvements


# Define the state that will be passed through the graph
class DirectorState(TypedDict):
    """State object for the Director workflow"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    project_id: str
    user_goal: str
    product_type: str
    target_platform: str
    matched_format: Optional[Dict[str, Any]]
    shot_list: Optional[List[Dict[str, Any]]]
    uploaded_segments: List[Dict[str, Any]]
    edited_video_path: Optional[str]
    current_step: str
    user_input_needed: bool
    next_instruction: str


class DirectorWorkflow:
    """
    Main Director Workflow using LangGraph.
    Coordinates all agents to guide users through video creation.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str):
        self.db = db
        self.api_key = api_key
        self.feedback_agent = FeedbackAgent(api_key)
        self.shot_list_manager = ShotListManager(api_key)
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(DirectorState)
        
        # Add nodes for each agent
        workflow.add_node("director", self.director_agent)
        workflow.add_node("format_matcher", self.format_matcher_agent)
        workflow.add_node("script_planner", self.script_planner_agent)
        workflow.add_node("recording_guide", self.recording_guide_agent)
        workflow.add_node("video_editor", self.video_editor_agent)
        workflow.add_node("export", self.export_agent)
        
        # Define the workflow edges
        workflow.set_entry_point("director")
        
        # Director routes to appropriate agent based on current step
        workflow.add_conditional_edges(
            "director",
            self.route_from_director,
            {
                "format_matcher": "format_matcher",
                "script_planner": "script_planner",
                "recording_guide": "recording_guide",
                "video_editor": "video_editor",
                "export": "export",
                "end": END
            }
        )
        
        # Agents route back to director only when needed
        workflow.add_edge("format_matcher", "director")
        workflow.add_edge("script_planner", END)  # End after script planning for user interaction
        workflow.add_edge("recording_guide", END)  # End after providing recording instructions
        workflow.add_edge("video_editor", "director")
        workflow.add_edge("export", END)
        
        return workflow.compile()
    
    def route_from_director(self, state: DirectorState) -> str:
        """Determine which agent to route to next"""
        current_step = state.get("current_step", "initial")
        
        # For initial project creation, go through format matching and script planning
        if current_step == "initial":
            return "format_matcher"
        elif current_step == "format_matched":
            return "script_planner"
        elif current_step in ["script_planned", "recording", "segments_uploaded"]:
            # Once script is planned, director handles all conversation
            # Director will internally route to specialized agents based on intent
            return "end"
        elif current_step == "editing_ready":
            return "video_editor"
        elif current_step == "video_edited":
            return "export"
        else:
            return "end"
    
    async def director_agent(self, state: DirectorState) -> DirectorState:
        """
        Director Agent - Conversational AI that understands intent and delegates tasks.
        Handles free-flowing conversation and routes to specialized agents.
        """
        current_step = state.get("current_step", "initial")
        messages = state.get("messages", [])
        
        # For initial setup, pass through to format matcher
        if current_step == "initial":
            return state
        
        # For format matching, coordinate workflow
        if current_step == "format_matched":
            return state
        
        # Get last user message
        last_message = messages[-1].content if messages else ""
        
        # Detect user intent and route appropriately
        intent = await self._detect_intent(last_message, state)
        
        # Handle different intents
        if intent["type"] == "feedback_request":
            response = await self._handle_feedback_request(intent, state)
        elif intent["type"] == "modify_shot_list":
            response = await self._handle_shot_list_modification(intent, state)
        elif intent["type"] == "project_status":
            response = await self._handle_status_request(state)
        elif intent["type"] == "recording_guidance":
            response = await self._handle_recording_guidance(intent, state)
        elif intent["type"] == "general_question":
            response = await self._handle_general_conversation(last_message, state)
        else:
            # Default conversational response
            response = await self._get_conversational_response(last_message, state)
        
        # Add response to messages
        state["messages"].append(AIMessage(content=response))
        
        # Update project state in database
        await self._save_project_state(state)
        
        return state
    
    async def _detect_intent(self, user_message: str, state: DirectorState) -> Dict[str, Any]:
        """
        Detect user intent from their message using LLM.
        
        Returns intent type and relevant parameters.
        """
        llm = LlmChat(
            api_key=self.api_key,
            session_id="intent_detector",
            system_message="You are an intent detection system."
        ).with_model("anthropic", "claude-3-7-sonnet-20250219")
        
        context = self._build_director_context(state)
        
        intent_prompt = f"""Analyze this user message and detect their intent:

**Context:**
{context}

**User Message:**
{user_message}

**Intent Categories:**
1. feedback_request - User wants feedback on a shot/video (keywords: feedback, how does, what do you think, review, analyze)
2. modify_shot_list - User wants to change shot list (keywords: add, remove, change, modify, different, instead)
3. project_status - User asks about progress (keywords: status, progress, what's left, done, remaining)
4. recording_guidance - User needs help recording (keywords: how to film, recording tips, camera setup)
5. general_question - General questions about process, format, etc.

Respond ONLY with JSON:
{{"type": "intent_type", "segment": "segment_name if applicable", "details": "key details"}}"""

        response = await llm.send_message(UserMessage(text=intent_prompt))
        
        # Parse JSON response (simplified - would have better error handling)
        try:
            return json.loads(response.strip())
        except:
            return {"type": "general_question", "details": user_message}
    
    async def _handle_feedback_request(self, intent: Dict, state: DirectorState) -> str:
        """Handle user request for feedback on uploaded content"""
        segment_name = intent.get("segment", "")
        shot_list = state.get("shot_list", [])
        
        # Find the shot they're asking about
        target_shot = None
        if segment_name:
            target_shot = next((s for s in shot_list if segment_name.lower() in s["segment_name"].lower()), None)
        
        if not target_shot:
            # Try to figure out which shot from context
            uploaded_shots = [s for s in shot_list if s.get("uploaded")]
            if uploaded_shots:
                target_shot = uploaded_shots[-1]  # Most recently uploaded
        
        if target_shot:
            # Get feedback from Feedback Agent
            feedback_result = await self.feedback_agent.analyze_shot(
                segment_name=target_shot["segment_name"],
                script=target_shot["script"],
                visual_guide=target_shot["visual_guide"],
                duration_target=target_shot["duration"],
                file_path=target_shot.get("file_path")
            )
            
            return f"""🎬 **Feedback on {target_shot['segment_name'].replace('_', ' ').title()}:**

{feedback_result['feedback']}

Want me to suggest improvements or analyze another shot?"""
        else:
            return "I don't see any uploaded shots yet. Upload a shot and I'll give you detailed feedback!"
    
    async def _handle_shot_list_modification(self, intent: Dict, state: DirectorState) -> str:
        """Handle user request to modify shot list"""
        shot_list = state.get("shot_list", [])
        user_request = intent.get("details", "")
        
        # Use Shot List Manager to modify
        result = await self.shot_list_manager.modify_shot_list(
            current_shot_list=shot_list,
            user_request=user_request,
            format_context=state.get("matched_format")
        )
        
        # Update state with new shot list (would parse from LLM response in production)
        # For now, keep original but show explanation
        
        return f"""✏️ **Shot List Updated:**

{result['modification_explanation']}

The shot list has been updated in the left panel. Review the changes and let me know if you want any adjustments!"""
    
    async def _handle_status_request(self, state: DirectorState) -> str:
        """Handle user asking about project status"""
        shot_list = state.get("shot_list", [])
        uploaded_count = sum(1 for s in shot_list if s.get("uploaded"))
        matched_format = state.get("matched_format")
        
        # Get overall feedback from Feedback Agent
        status = await get_overall_project_feedback(
            api_key=self.api_key,
            shot_list=shot_list,
            uploaded_count=uploaded_count,
            matched_format=matched_format
        )
        
        return f"""📊 **Project Status:**

{status}"""
    
    async def _handle_recording_guidance(self, intent: Dict, state: DirectorState) -> str:
        """Handle user asking for recording help"""
        shot_list = state.get("shot_list", [])
        details = intent.get("details", "")
        
        # Find next unrecorded shot
        next_shot = next((s for s in shot_list if not s.get("uploaded")), None)
        
        if next_shot:
            return f"""🎥 **Recording Guide for {next_shot['segment_name'].replace('_', ' ').title()}:**

**Duration Target:** {next_shot['duration']} seconds

**What to Say:**
{next_shot['script']}

**How to Film:**
{next_shot['visual_guide']}

**Pro Tips:**
• Film in good natural light or use a ring light
• Hold phone steady or use tripod
• Speak with energy and confidence
• Do 2-3 takes and pick the best one
• Check audio levels - voice should be clear

Need help with something specific? Just ask!"""
        else:
            return "All shots have been uploaded! Ready to move to editing?"
    
    async def _handle_general_conversation(self, message: str, state: DirectorState) -> str:
        """Handle general questions and conversation"""
        return await self._get_conversational_response(message, state)
    
    async def _get_conversational_response(self, message: str, state: DirectorState) -> str:
        """Get a conversational response from Director"""
        llm = LlmChat(
            api_key=self.api_key,
            session_id=state.get("project_id", "default"),
            system_message=self._get_conversational_prompt()
        ).with_model("anthropic", "claude-3-7-sonnet-20250219")
        
        context = self._build_director_context(state)
        
        director_input = f"""{context}

User: {message}

Respond conversationally and helpfully. If they need help with anything, offer specific guidance."""
        
        response = await llm.send_message(UserMessage(text=director_input))
        return response
    
    async def format_matcher_agent(self, state: DirectorState) -> DirectorState:
        """
        Format Matcher Agent - Matches user's goal with viral formats.
        """
        user_goal = state.get("user_goal", "")
        product_type = state.get("product_type", "")
        target_platform = state.get("target_platform", "")
        
        # Query viral formats from database
        formats = await query_viral_formats(
            self.db,
            platform=target_platform
        )
        
        # Calculate match scores
        format_scores = []
        for fmt in formats:
            score = await calculate_format_match_score(
                user_goal, product_type, target_platform, fmt
            )
            format_scores.append((fmt, score))
        
        # Sort by score and get best match
        format_scores.sort(key=lambda x: x[1], reverse=True)
        best_format = format_scores[0][0] if format_scores else None
        
        if best_format:
            state["matched_format"] = best_format
            state["current_step"] = "format_matched"
            
            # Create message about matched format
            format_message = f"""🎯 Perfect! I found the ideal format for your video: **{best_format['name']}**

{best_format['description']}

This format typically performs well on {', '.join(best_format['platform_fit'])} and includes {len(best_format['structure'])} key segments:
{self._format_structure_summary(best_format['structure'])}

This format has a viral score of {best_format['success_metrics']['viral_score']}/100 based on past performance.

Ready to move forward with this format?"""
            
            state["messages"].append(AIMessage(content=format_message))
        else:
            state["messages"].append(AIMessage(content="I couldn't find a perfect format match. Let me create a custom format for you..."))
        
        # Save project state to database
        await self._save_project_state(state)
        
        return state
    
    async def script_planner_agent(self, state: DirectorState) -> DirectorState:
        """
        Script Planner Agent - Creates detailed shot list and scripts.
        """
        matched_format = state.get("matched_format")
        user_goal = state.get("user_goal", "")
        
        if not matched_format:
            return state
        
        # Generate customized shot list based on format structure
        shot_list = []
        for segment in matched_format["structure"]:
            shot = {
                "segment_name": segment["segment"],
                "duration": segment["duration"],
                "script": segment["script_template"],
                "visual_guide": segment["visual_guide"],
                "required": segment["required"],
                "uploaded": False
            }
            shot_list.append(shot)
        
        state["shot_list"] = shot_list
        state["current_step"] = "script_planned"
        
        # Create detailed shot list message
        shot_list_message = f"""📝 Here's your complete shot list for the video:

{self._format_shot_list(shot_list)}

**Total Duration:** ~{sum(s['duration'] for s in shot_list)} seconds

I'll guide you through recording each segment step by step. Ready to start?"""
        
        state["messages"].append(AIMessage(content=shot_list_message))
        
        # Save project state to database
        await self._save_project_state(state)
        
        return state
    
    async def recording_guide_agent(self, state: DirectorState) -> DirectorState:
        """
        Recording Guide Agent - Provides step-by-step recording instructions.
        """
        shot_list = state.get("shot_list", [])
        uploaded_segments = state.get("uploaded_segments", [])
        
        # Find next segment to record
        next_segment = None
        for shot in shot_list:
            if not shot.get("uploaded", False):
                next_segment = shot
                break
        
        if next_segment:
            guide_message = f"""🎬 Let's record: **{next_segment['segment_name'].upper()}**

⏱️ **Duration:** {next_segment['duration']} seconds

📝 **Script:**
{next_segment['script']}

🎥 **How to film this:**
{next_segment['visual_guide']}

**Tips:**
• Film in good lighting
• Hold your phone steady (or use a tripod)
• Speak clearly and with energy
• Keep it within {next_segment['duration']} seconds

Upload your video when ready, and I'll validate it before we move to the next segment!"""
            
            state["messages"].append(AIMessage(content=guide_message))
            state["user_input_needed"] = True
            state["next_instruction"] = "upload_segment"
        else:
            # All segments uploaded
            state["current_step"] = "segments_uploaded"
            state["messages"].append(AIMessage(content="✅ All segments recorded! Now let's edit them together..."))
        
        return state
    
    async def video_editor_agent(self, state: DirectorState) -> DirectorState:
        """
        Video Editor Agent - Performs video editing using FFMPEG tools.
        """
        uploaded_segments = state.get("uploaded_segments", [])
        shot_list = state.get("shot_list", [])
        
        if not uploaded_segments:
            return state
        
        editing_steps = []
        
        # Step 1: Merge all segments
        video_files = [seg["file_path"] for seg in uploaded_segments]
        merge_result = await ffmpeg_merge_videos(
            input_files=video_files,
            output_file=f"merged_{state['project_id']}.mp4"
        )
        
        if merge_result["success"]:
            editing_steps.append("✅ Merged all segments")
            merged_path = merge_result["output_file"]
            
            # Step 2: Add subtitles (placeholder - would need actual subtitle data)
            # For MVP, we'll skip complex subtitle generation
            
            # Step 3: Add transitions (if needed)
            # This would require more complex logic
            
            state["edited_video_path"] = merged_path
            state["current_step"] = "video_edited"
            
            edit_message = f"""🎞️ Video editing complete!

Editing steps performed:
{chr(10).join(editing_steps)}

Your video is ready for final optimization and export. Which platform should we optimize it for?"""
            
            state["messages"].append(AIMessage(content=edit_message))
        else:
            state["messages"].append(AIMessage(content=f"❌ Video editing failed: {merge_result['error']}"))
        
        return state
    
    async def export_agent(self, state: DirectorState) -> DirectorState:
        """
        Export Agent - Optimizes and exports final video for platform.
        """
        edited_video = state.get("edited_video_path")
        target_platform = state.get("target_platform", "youtube")
        
        if not edited_video:
            return state
        
        # Optimize for platform
        export_result = await optimize_for_platform(
            input_file=edited_video,
            output_file=f"final_{state['project_id']}_{target_platform}.mp4",
            platform=target_platform
        )
        
        if export_result["success"]:
            state["current_step"] = "complete"
            
            final_message = f"""🎉 Your video is ready!

✅ Optimized for {target_platform}
📁 **Download:** {export_result['output_file']}

Your video is now perfectly formatted for {target_platform} with the right dimensions, bitrate, and compression.

Want to export for other platforms too?"""
            
            state["messages"].append(AIMessage(content=final_message))
        else:
            state["messages"].append(AIMessage(content=f"❌ Export failed: {export_result['error']}"))
        
        return state
    
    # Helper methods
    
    def _get_director_prompt(self) -> str:
        """System prompt for Director Agent"""
        return """You are an AI Director for filmit! - a conversational video creation coach.

**Your Role:**
- Have natural, helpful conversations with creators
- Understand their intent and delegate to specialized agents
- Provide feedback, guidance, and encouragement
- Help them create viral-worthy content

**Your Specialized Agents:**
- Format Matcher: Matches viral video formats
- Script Planner: Creates shot lists
- Feedback Agent: Analyzes uploaded shots and gives constructive feedback
- Shot List Manager: Modifies shots based on user requests
- Recording Guide: Provides filming instructions
- Video Editor: Edits videos with FFMPEG
- Export Agent: Optimizes for platforms

**Your Approach:**
- Be conversational, not robotic
- Ask clarifying questions when needed
- Give specific, actionable advice
- Celebrate wins and provide constructive feedback
- Delegate tasks to agents when appropriate
- Keep them focused but flexible

You're their creative partner, not just a tool."""
    
    def _get_conversational_prompt(self) -> str:
        """System prompt for conversational responses"""
        return """You are a friendly, expert video director having a conversation with a creator.

Be:
- Conversational and warm
- Specific and actionable
- Encouraging but honest
- Reference viral video best practices
- Quick to delegate to specialized agents when needed

Don't:
- Be overly formal or robotic
- Give vague advice
- Ignore their specific questions
- Make them feel bad about mistakes

You're their coach and partner in creating viral content."""
    
    def _build_director_context(self, state: DirectorState) -> str:
        """Build context summary for director"""
        context_parts = [f"Current Step: {state.get('current_step', 'initial')}"]
        
        if state.get("user_goal"):
            context_parts.append(f"User Goal: {state['user_goal']}")
        
        if state.get("matched_format"):
            context_parts.append(f"Format: {state['matched_format']['name']}")
        
        if state.get("shot_list"):
            completed = sum(1 for s in state['shot_list'] if s.get('uploaded'))
            total = len(state['shot_list'])
            context_parts.append(f"Recording Progress: {completed}/{total} segments")
        
        return "\n".join(context_parts)
    
    def _format_structure_summary(self, structure: List[Dict]) -> str:
        """Format structure summary for display"""
        summary = []
        for i, seg in enumerate(structure, 1):
            summary.append(f"{i}. **{seg['segment'].title()}** ({seg['duration']}s): {seg['script_template'][:50]}...")
        return "\n".join(summary)
    
    def _format_shot_list(self, shot_list: List[Dict]) -> str:
        """Format shot list for display"""
        formatted = []
        for i, shot in enumerate(shot_list, 1):
            status = "✅" if shot.get("uploaded") else "⏳"
            formatted.append(
                f"{status} **Segment {i}: {shot['segment_name'].title()}** ({shot['duration']}s)\n"
                f"   Script: {shot['script']}\n"
                f"   Visual: {shot['visual_guide']}"
            )
        return "\n\n".join(formatted)
    
    async def _save_project_state(self, state: DirectorState):
        """Save project state to MongoDB"""
        # Convert messages to serializable format
        messages_data = []
        for msg in state.get("messages", []):
            if hasattr(msg, 'content'):
                msg_type = "human" if msg.__class__.__name__ == "HumanMessage" else "ai"
                messages_data.append({
                    "type": msg_type,
                    "content": msg.content,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        project_data = {
            "project_id": state["project_id"],
            "user_id": state.get("user_id"),  # Save user ID
            "user_goal": state.get("user_goal", ""),
            "product_type": state.get("product_type", ""),
            "target_platform": state.get("target_platform", ""),
            "matched_format": state.get("matched_format"),
            "shot_list": state.get("shot_list"),
            "uploaded_segments": state.get("uploaded_segments", []),
            "edited_video_path": state.get("edited_video_path"),
            "current_step": state.get("current_step"),
            "messages": messages_data,  # Save messages!
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.video_projects.update_one(
            {"project_id": state["project_id"]},
            {"$set": project_data},
            upsert=True
        )