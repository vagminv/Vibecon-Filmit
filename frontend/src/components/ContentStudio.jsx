import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Input } from './ui/input';
import { 
  Sparkles, Upload, X, Send, Video, CheckCircle, XCircle, 
  Film, Loader2, User, Clock, ChevronLeft, FolderOpen, Clapperboard,
  Download, Settings, Edit2, Trash2, Save, Plus, GripVertical
} from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate, useParams } from 'react-router-dom';
import { UserMenu } from './UserMenu';
import {
  sendDirectorMessage,
  getDirectorProject,
  uploadDirectorSegment,
  assembleProjectVideo,
  getAssemblyStatus,
  downloadAssembledVideo,
  updateShot,
  addShot,
  deleteShot,
  reorderShots
} from '../utils/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Progress } from "./ui/progress";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Sortable Shot Card Component
const SortableShotCard = ({ shot, index, projectId, onUpdate, onDelete, uploadingSegment, handleSegmentUpload, handleFeedback }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    segment_name: shot.segment_name,
    script: shot.script,
    visual_guide: shot.visual_guide,
    duration: shot.duration
  });

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: shot.segment_name + index });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleSave = async () => {
    try {
      const result = await updateShot(projectId, index, editData);
      if (result.success) {
        onUpdate(result.shot_list);
        setIsEditing(false);
        toast.success('Shot updated successfully!');
      }
    } catch (error) {
      console.error('Error updating shot:', error);
      toast.error('Failed to update shot');
    }
  };

  const handleCancel = () => {
    setEditData({
      segment_name: shot.segment_name,
      script: shot.script,
      visual_guide: shot.visual_guide,
      duration: shot.duration
    });
    setIsEditing(false);
  };

  const handleDeleteClick = async () => {
    console.log('Delete button clicked for shot:', shot.segment_name, 'index:', index);
    
    const confirmed = window.confirm(`Are you sure you want to delete "${shot.segment_name.replace('_', ' ')}"?`);
    console.log('User confirmation:', confirmed);
    
    if (confirmed) {
      try {
        console.log('Calling deleteShot API with projectId:', projectId, 'index:', index);
        const result = await deleteShot(projectId, index);
        console.log('Delete API response:', result);
        
        if (result.success) {
          onDelete(result.shot_list);
          toast.success('Shot deleted successfully!');
        } else {
          toast.error('Failed to delete shot');
        }
      } catch (error) {
        console.error('Error deleting shot:', error);
        toast.error(`Failed to delete shot: ${error.message}`);
      }
    }
  };

  return (
    <Card 
      ref={setNodeRef}
      style={style}
      className={`transition-all ${
        shot.uploaded 
          ? 'bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800' 
          : 'bg-card border-border hover:border-primary/50'
      }`}
    >
      <CardContent className="pt-4 pb-4">
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 flex-1">
              <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing">
                <GripVertical className="w-4 h-4 text-muted-foreground" />
              </div>
              {shot.uploaded ? (
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
              ) : (
                <Clock className="w-5 h-5 text-muted-foreground flex-shrink-0" />
              )}
              <div className="flex-1">
                {isEditing ? (
                  <Input
                    value={editData.segment_name}
                    onChange={(e) => setEditData({...editData, segment_name: e.target.value})}
                    className="text-sm font-semibold mb-2"
                  />
                ) : (
                  <h4 className="font-semibold text-sm text-foreground capitalize">
                    {shot.segment_name.replace('_', ' ')}
                  </h4>
                )}
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  {isEditing ? (
                    <Input
                      type="number"
                      value={editData.duration}
                      onChange={(e) => setEditData({...editData, duration: parseInt(e.target.value)})}
                      className="w-16 h-6 text-xs"
                    />
                  ) : (
                    <Badge variant="outline" className="text-xs">
                      {shot.duration}s
                    </Badge>
                  )}
                  {shot.uploaded && !isEditing && (
                    <button
                      onClick={() => handleFeedback(shot.segment_name)}
                      className="text-xs text-primary hover:underline font-semibold"
                    >
                      Get Feedback
                    </button>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-1">
              {isEditing ? (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleSave}
                    className="h-8 w-8 p-0"
                  >
                    <Save className="w-4 h-4 text-green-600" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCancel}
                    className="h-8 w-8 p-0"
                  >
                    <X className="w-4 h-4 text-red-600" />
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditing(true)}
                    className="h-8 w-8 p-0"
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteClick();
                    }}
                    className="h-8 w-8 p-0"
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </Button>
                </>
              )}
            </div>
          </div>
          
          <div className="space-y-2 text-xs">
            <div>
              <strong className="text-foreground">Script:</strong>
              {isEditing ? (
                <Textarea
                  value={editData.script}
                  onChange={(e) => setEditData({...editData, script: e.target.value})}
                  className="mt-1 text-xs min-h-[60px]"
                />
              ) : (
                <p className="text-muted-foreground mt-1">{shot.script}</p>
              )}
            </div>
            <div>
              <strong className="text-foreground">Visual Guide:</strong>
              {isEditing ? (
                <Textarea
                  value={editData.visual_guide}
                  onChange={(e) => setEditData({...editData, visual_guide: e.target.value})}
                  className="mt-1 text-xs min-h-[60px]"
                />
              ) : (
                <p className="text-muted-foreground mt-1">{shot.visual_guide}</p>
              )}
            </div>
          </div>

          {!isEditing && (
            <Button
              size="sm"
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'video/*';
                input.onchange = (e) => {
                  const file = e.target.files[0];
                  if (file) handleSegmentUpload(shot, file);
                };
                input.click();
              }}
              disabled={uploadingSegment === shot.segment_name}
              className="w-full"
              variant={shot.uploaded ? "secondary" : "outline"}
            >
              {uploadingSegment === shot.segment_name ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : shot.uploaded ? (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Replace Footage
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Footage
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Function to convert markdown to plain text
const markdownToPlainText = (text) => {
  if (!text) return '';
  
  return text
    // Remove headers (###, ##, #)
    .replace(/^#{1,6}\s+/gm, '')
    // Remove bold (**text** or __text__)
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    // Remove italic (*text* or _text_)
    .replace(/(\*|_)(.*?)\1/g, '$2')
    // Remove strikethrough (~~text~~)
    .replace(/~~(.*?)~~/g, '$1')
    // Remove inline code (`code`)
    .replace(/`([^`]+)`/g, '$1')
    // Remove code blocks (```code```)
    .replace(/```[\s\S]*?```/g, '')
    // Remove links [text](url)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove images ![alt](url)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    // Remove horizontal rules (---, ___, ***)
    .replace(/^[\*\-_]{3,}\s*$/gm, '')
    // Remove blockquotes (>)
    .replace(/^>\s+/gm, '')
    // Remove list markers (-, *, +, 1.)
    .replace(/^\s*[-\*\+]\s+/gm, '• ')
    .replace(/^\s*\d+\.\s+/gm, '')
    // Remove extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

// Function to extract clean user goal without research context
const extractCleanUserGoal = (userGoal) => {
  if (!userGoal) return '';
  
  // Split by research context marker and return only the first part
  const parts = userGoal.split(/\[Research Context for AI Director\]:/i);
  return parts[0].trim();
};

export const ContentStudio = () => {
  const navigate = useNavigate();
  const { projectId } = useParams();
  
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [shotList, setShotList] = useState([]);
  const [matchedFormat, setMatchedFormat] = useState(null);
  const [uploadingSegment, setUploadingSegment] = useState(null);
  const [showAddShot, setShowAddShot] = useState(false);
  const [newShotData, setNewShotData] = useState({
    segment_name: '',
    script: '',
    visual_guide: '',
    duration: 15
  });
  
  // Assembly state
  const [showAssemblyDialog, setShowAssemblyDialog] = useState(false);
  const [isAssembling, setIsAssembling] = useState(false);
  const [assemblyId, setAssemblyId] = useState(null);
  const [assemblyProgress, setAssemblyProgress] = useState(0);
  const [assemblyStatus, setAssemblyStatus] = useState(null);
  const [assemblyOptions, setAssemblyOptions] = useState({
    add_transitions: true,
    transition_type: 'fade',
    transition_duration: 0.8,
    add_subtitles: true,
    subtitle_position: 'bottom',
    subtitle_font_size: 48,
    optimize_platform: 'youtube'
  });
  
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load project on mount
  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      const projectData = await getDirectorProject(projectId);
      setProject(projectData);
      
      if (projectData.shot_list) {
        setShotList(projectData.shot_list);
      }
      if (projectData.matched_format) {
        setMatchedFormat(projectData.matched_format);
      }
      
      // Load messages from database if they exist
      if (projectData.messages && projectData.messages.length > 0) {
        const loadedMessages = projectData.messages.map(msg => ({
          role: msg.type === 'human' ? 'user' : 'assistant',
          content: msg.content,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date()
        }));
        setMessages(loadedMessages);
      } else {
        // Initialize with welcome message only if no messages exist
        const shotCount = projectData.shot_list ? projectData.shot_list.length : 0;
        const formatName = projectData.matched_format ? projectData.matched_format.name : 'a viral format';
        const platform = projectData.target_platform || 'your platform';
        
        const summary = `You're creating content for ${platform} using the "${formatName}" format with ${shotCount} shots to film.`;
        
        setMessages([{
          role: 'assistant',
          content: `I've created your shot list based on the best viral format for your content. ${summary} Ready to start recording?`,
          timestamp: new Date()
        }]);
      }
    } catch (error) {
      console.error('Error loading project:', error);
      toast.error('Failed to load project');
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    setIsProcessing(true);
    const userMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    try {
      const result = await sendDirectorMessage(projectId, userMessage.content);
      
      const aiMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);

      // Update state from result
      if (result.shot_list) {
        setShotList(result.shot_list);
      }
      if (result.matched_format) {
        setMatchedFormat(result.matched_format);
      }

    } catch (error) {
      console.error('Director error:', error);
      toast.error('Failed to send message');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSendMessage();
    }
  };

  const handleSegmentUpload = async (segment, file) => {
    if (!file.type.startsWith('video/')) {
      toast.error('Please upload a video file');
      return;
    }

    setUploadingSegment(segment.segment_name);
    try {
      await uploadDirectorSegment(projectId, segment.segment_name, file);
      
      toast.success(`${segment.segment_name} uploaded successfully!`);
      
      // Update shot list
      setShotList(prev => prev.map(s => 
        s.segment_name === segment.segment_name 
          ? { ...s, uploaded: true }
          : s
      ));
      
      // Reload project to get latest state
      await loadProject();
      
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload segment');
    } finally {
      setUploadingSegment(null);
    }
  };

  const allSegmentsUploaded = () => {
    return shotList.length > 0 && shotList.every(shot => shot.uploaded);
  };

  const handleStartAssembly = async () => {
    setIsAssembling(true);
    setAssemblyProgress(0);
    
    try {
      const result = await assembleProjectVideo(projectId, assemblyOptions);
      
      setAssemblyId(result.assembly_id);
      setAssemblyStatus('processing');
      toast.success('Video assembly started!');
      
      // Start polling for status
      pollAssemblyStatus(result.assembly_id);
      
    } catch (error) {
      console.error('Assembly error:', error);
      toast.error('Failed to start video assembly');
      setIsAssembling(false);
    }
  };

  const pollAssemblyStatus = async (id) => {
    const checkStatus = async () => {
      try {
        const status = await getAssemblyStatus(id);
        
        setAssemblyProgress(status.progress);
        setAssemblyStatus(status.status);
        
        if (status.status === 'completed') {
          setIsAssembling(false);
          toast.success('Video assembly complete! Ready to download.');
        } else if (status.status === 'failed') {
          setIsAssembling(false);
          toast.error(`Assembly failed: ${status.error || 'Unknown error'}`);
        } else {
          // Continue polling
          setTimeout(() => checkStatus(), 2000);
        }
      } catch (error) {
        console.error('Status check error:', error);
        setIsAssembling(false);
        toast.error('Failed to check assembly status');
      }
    };
    
    checkStatus();
  };

  const handleDownloadVideo = async () => {
    try {
      await downloadAssembledVideo(assemblyId);
      toast.success('Video download started!');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download video');
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;

    if (active.id !== over.id) {
      const oldIndex = shotList.findIndex((shot, idx) => shot.segment_name + idx === active.id);
      const newIndex = shotList.findIndex((shot, idx) => shot.segment_name + idx === over.id);

      const newShotList = arrayMove(shotList, oldIndex, newIndex);
      setShotList(newShotList);

      try {
        await reorderShots(projectId, newShotList);
        toast.success('Shot list reordered!');
      } catch (error) {
        console.error('Error reordering shots:', error);
        toast.error('Failed to reorder shots');
        setShotList(shotList); // Revert on error
      }
    }
  };

  const handleAddShot = async () => {
    if (!newShotData.segment_name.trim() || !newShotData.script.trim()) {
      toast.error('Please fill in shot name and script');
      return;
    }

    try {
      const result = await addShot(projectId, newShotData);
      if (result.success) {
        setShotList(result.shot_list);
        setShowAddShot(false);
        setNewShotData({
          segment_name: '',
          script: '',
          visual_guide: '',
          duration: 15
        });
        toast.success('Shot added successfully!');
      }
    } catch (error) {
      console.error('Error adding shot:', error);
      toast.error('Failed to add shot');
    }
  };

  const handleFeedback = async (segmentName) => {
    const msg = `Can you give me feedback on the ${segmentName.replace('_', ' ')} shot?`;
    setInputValue(msg);
    
    setIsProcessing(true);
    const userMessage = {
      role: 'user',
      content: msg,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    
    try {
      const result = await sendDirectorMessage(projectId, msg);
      const aiMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      if (result.shot_list) setShotList(result.shot_list);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to get feedback');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-sky">
      {/* Navigation */}
      <nav className="border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-full px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/director')}
                className="gap-2"
              >
                <ChevronLeft className="w-4 h-4" />
                Back to Home
              </Button>
              <div className="h-6 w-px bg-border"></div>
              <Badge className="bg-primary/20 text-primary border-primary/30 font-sans animate-pulse">
                <Film className="w-3 h-3 mr-1" />
                Content Studio
              </Badge>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/director/projects')}
                className="gap-2"
              >
                <FolderOpen className="w-4 h-4" />
                All Projects
              </Button>
              <UserMenu />
            </div>
          </div>
        </div>
      </nav>

      {/* Split Screen Layout */}
      <div className="flex h-[calc(100vh-4rem)]">
        
        {/* Left Side - Shot List & Project Info */}
        <div className="w-1/3 border-r border-border/50 bg-background/50 backdrop-blur-sm overflow-y-auto">
          <div className="p-6 space-y-6">
            
            {/* Project Info */}
            {project && (
              <Card className="border-primary/30 bg-primary/5">
                <CardContent className="pt-4 pb-4">
                  <h3 className="text-sm font-semibold text-muted-foreground mb-2">Project Goal</h3>
                  <p className="text-sm text-foreground">{extractCleanUserGoal(project.user_goal)}</p>
                </CardContent>
              </Card>
            )}

            {/* Matched Format */}
            {matchedFormat && (
              <Card className="border-accent/30 bg-accent/5">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-accent-foreground" />
                    <h3 className="text-sm font-semibold text-foreground">Matched Format</h3>
                  </div>
                  <p className="text-sm font-semibold text-foreground mb-1">{matchedFormat.name}</p>
                  <p className="text-xs text-muted-foreground">{matchedFormat.description}</p>
                </CardContent>
              </Card>
            )}

            {/* Shot List */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-foreground">Shot List</h3>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {shotList.filter(s => s.uploaded).length} / {shotList.length}
                  </Badge>
                  <Button
                    size="sm"
                    onClick={() => setShowAddShot(true)}
                    className="gap-1 h-7"
                  >
                    <Plus className="w-4 h-4" />
                    Add Shot
                  </Button>
                </div>
              </div>

              {/* Add Shot Form */}
              {showAddShot && (
                <Card className="border-primary/30 bg-primary/5">
                  <CardContent className="pt-4 pb-4 space-y-3">
                    <h4 className="font-semibold text-sm">Add New Shot</h4>
                    <div className="space-y-2">
                      <Input
                        placeholder="Shot name (e.g., hook, demo)"
                        value={newShotData.segment_name}
                        onChange={(e) => setNewShotData({...newShotData, segment_name: e.target.value})}
                        className="text-sm"
                      />
                      <Textarea
                        placeholder="Script for this shot"
                        value={newShotData.script}
                        onChange={(e) => setNewShotData({...newShotData, script: e.target.value})}
                        className="text-sm min-h-[60px]"
                      />
                      <Textarea
                        placeholder="Visual guide (how to film)"
                        value={newShotData.visual_guide}
                        onChange={(e) => setNewShotData({...newShotData, visual_guide: e.target.value})}
                        className="text-sm min-h-[60px]"
                      />
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground">Duration (seconds):</label>
                        <Input
                          type="number"
                          value={newShotData.duration}
                          onChange={(e) => setNewShotData({...newShotData, duration: parseInt(e.target.value)})}
                          className="w-20 h-8 text-sm"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleAddShot} className="flex-1">
                        <Plus className="w-4 h-4 mr-1" />
                        Add Shot
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => {
                          setShowAddShot(false);
                          setNewShotData({
                            segment_name: '',
                            script: '',
                            visual_guide: '',
                            duration: 15
                          });
                        }}
                        className="flex-1"
                      >
                        Cancel
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
              
              {/* Sortable Shot List */}
              {shotList.length > 0 && (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={shotList.map((shot, idx) => shot.segment_name + idx)}
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-3">
                      {shotList.map((shot, index) => (
                        <SortableShotCard
                          key={shot.segment_name + index}
                          shot={shot}
                          index={index}
                          projectId={projectId}
                          onUpdate={setShotList}
                          onDelete={setShotList}
                          uploadingSegment={uploadingSegment}
                          handleSegmentUpload={handleSegmentUpload}
                          handleFeedback={handleFeedback}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </DndContext>
              )}
              
              {/* Generate Video Button - Below Shot Cards */}
              {shotList.length > 0 && (
                <div className="pt-4 space-y-3">
                  {!isAssembling && !assemblyId && (
                    <Button 
                      onClick={() => {
                        // Check if any shots have footage uploaded
                        const hasUploads = shotList.some(shot => shot.uploaded);
                        if (!hasUploads) {
                          toast.error('Please upload footage for at least one shot before generating the video.', {
                            description: 'Click the "Upload Footage" button on any shot to add your video clips.',
                            duration: 5000
                          });
                          return;
                        }
                        setShowAssemblyDialog(true);
                      }}
                      className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold shadow-lg"
                      size="lg"
                    >
                      <Clapperboard className="w-5 h-5 mr-2" />
                      Generate Video
                    </Button>
                  )}
                  
                  {isAssembling && (
                    <Card className="border-primary/20 bg-gradient-to-br from-background to-primary/5">
                      <CardContent className="pt-4 pb-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Generating video...</span>
                            <span className="font-semibold text-foreground">{assemblyProgress}%</span>
                          </div>
                          <Progress value={assemblyProgress} className="h-2" />
                          <p className="text-xs text-muted-foreground">
                            {assemblyProgress < 30 && "Processing segments..."}
                            {assemblyProgress >= 30 && assemblyProgress < 60 && "Adding transitions..."}
                            {assemblyProgress >= 60 && assemblyProgress < 90 && "Optimizing video..."}
                            {assemblyProgress >= 90 && "Finalizing..."}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  
                  {assemblyStatus === 'completed' && assemblyId && (
                    <div className="space-y-2">
                      <Button 
                        onClick={handleDownloadVideo}
                        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold shadow-lg"
                        size="lg"
                      >
                        <Download className="w-5 h-5 mr-2" />
                        Download Video
                      </Button>
                      <Button 
                        onClick={() => setShowAssemblyDialog(true)}
                        variant="outline"
                        className="w-full border-primary/30 hover:bg-primary/5"
                        size="lg"
                      >
                        <Settings className="w-5 h-5 mr-2" />
                        Regenerate Video
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side - Chat */}
        <div className="flex-1 flex flex-col">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message, index) => (
              <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && (
                  <Avatar className="w-10 h-10 border-2 border-primary/20 flex-shrink-0">
                    <AvatarFallback className="bg-gradient-primary text-primary-foreground">
                      <Sparkles className="w-5 h-5" />
                    </AvatarFallback>
                  </Avatar>
                )}
                
                <div className={`flex-1 max-w-2xl ${message.role === 'user' ? 'flex flex-col items-end' : ''}`}>
                  <Card className={`${
                    message.role === 'user' 
                      ? 'bg-primary text-primary-foreground border-primary' 
                      : 'bg-card/95 backdrop-blur-sm border-border/50'
                  } shadow-lg`}>
                    <CardContent className="pt-4 pb-4">
                      <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
                        {message.role === 'assistant' ? markdownToPlainText(message.content) : message.content}
                      </div>
                    </CardContent>
                  </Card>
                  <span className="text-xs text-muted-foreground mt-1.5 font-sans">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {message.role === 'user' && (
                  <Avatar className="w-10 h-10 border-2 border-primary/20 flex-shrink-0">
                    <AvatarFallback className="bg-muted text-muted-foreground">
                      <User className="w-5 h-5" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}

            {isProcessing && (
              <div className="flex gap-3 justify-start">
                <Avatar className="w-10 h-10 border-2 border-primary/20">
                  <AvatarFallback className="bg-gradient-primary text-primary-foreground">
                    <Sparkles className="w-5 h-5" />
                  </AvatarFallback>
                </Avatar>
                <Card className="bg-card/95 backdrop-blur-sm border-border/50 shadow-lg">
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0s' }}></div>
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                      <span className="text-sm text-muted-foreground font-sans">Thinking...</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm p-6">
            {/* Quick Actions */}
            {shotList.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setInputValue("Please provide a comprehensive project status. Include: 1) Overall creative vision and format we're using, 2) Complete shot list with what's been filmed and what's remaining, 3) Quality assessment of uploaded shots so far, 4) Any creative adjustments or suggestions based on progress, 5) Estimated completion percentage and next steps.");
                    textareaRef.current?.focus();
                  }}
                  className="text-xs"
                >
                  📊 Project Status
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setInputValue("Please explain the next shot I need to record. Include: 1) Which shot it is in the sequence, 2) What the script and visual guide are for this shot, 3) Any specific tips or techniques for filming this shot effectively, 4) How this shot fits into the overall narrative. Do I have any questions before I start filming?");
                    textareaRef.current?.focus();
                  }}
                  className="text-xs"
                >
                  🎥 Next Shot
                </Button>
                {shotList.some(s => s.uploaded) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setInputValue("Can you review all my uploaded shots?");
                      textareaRef.current?.focus();
                    }}
                    className="text-xs"
                  >
                    ✨ Review Uploads
                  </Button>
                )}
              </div>
            )}
            
            <Card className="border-border/50 shadow-xl bg-card/95 backdrop-blur-sm">
              <CardContent className="pt-4 pb-4">
                <div className="flex gap-2">
                  <Textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything about your video or tell me you're ready to record..."
                    className="min-h-[80px] resize-none focus:ring-primary font-sans text-base"
                    disabled={isProcessing}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={isProcessing || !inputValue.trim()}
                    className="bg-gradient-primary hover:shadow-glow self-end px-5 h-[80px] transition-all duration-300"
                  >
                    <Send className="w-5 h-5" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2 font-sans">
                  Press <kbd className="px-2 py-1 bg-muted rounded text-xs">⌘ Enter</kbd> to send
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Assembly Configuration Dialog */}
      <Dialog open={showAssemblyDialog} onOpenChange={setShowAssemblyDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Clapperboard className="w-5 h-5" />
              Generate Video
            </DialogTitle>
            <DialogDescription>
              Your video clips will be merged together into one continuous video.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            
            {/* Transitions */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="transitions" className="text-base font-semibold">Add Transitions</Label>
                  <p className="text-sm text-muted-foreground">Smooth transitions between shots</p>
                </div>
                <Switch
                  id="transitions"
                  checked={assemblyOptions.add_transitions}
                  onCheckedChange={(checked) => 
                    setAssemblyOptions(prev => ({ ...prev, add_transitions: checked }))
                  }
                />
              </div>
              
              {assemblyOptions.add_transitions && (
                <div className="grid grid-cols-2 gap-4 pl-4">
                  <div className="space-y-2">
                    <Label htmlFor="transition-type">Transition Type</Label>
                    <Select
                      value={assemblyOptions.transition_type}
                      onValueChange={(value) => 
                        setAssemblyOptions(prev => ({ ...prev, transition_type: value }))
                      }
                    >
                      <SelectTrigger id="transition-type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fade">Fade</SelectItem>
                        <SelectItem value="wipe">Wipe</SelectItem>
                        <SelectItem value="dissolve">Dissolve</SelectItem>
                        <SelectItem value="slidedown">Slide Down</SelectItem>
                        <SelectItem value="slideup">Slide Up</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="transition-duration">Duration (seconds)</Label>
                    <input
                      id="transition-duration"
                      type="number"
                      min="0.1"
                      max="2"
                      step="0.1"
                      value={assemblyOptions.transition_duration}
                      onChange={(e) => 
                        setAssemblyOptions(prev => ({ 
                          ...prev, 
                          transition_duration: parseFloat(e.target.value) 
                        }))
                      }
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="border-t pt-4" />
            
            {/* Subtitles */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="subtitles" className="text-base font-semibold">Add Subtitles</Label>
                  <p className="text-sm text-muted-foreground">Auto-generated from shot scripts</p>
                </div>
                <Switch
                  id="subtitles"
                  checked={assemblyOptions.add_subtitles}
                  onCheckedChange={(checked) => 
                    setAssemblyOptions(prev => ({ ...prev, add_subtitles: checked }))
                  }
                />
              </div>
              
              {assemblyOptions.add_subtitles && (
                <div className="grid grid-cols-2 gap-4 pl-4">
                  <div className="space-y-2">
                    <Label htmlFor="subtitle-position">Position</Label>
                    <Select
                      value={assemblyOptions.subtitle_position}
                      onValueChange={(value) => 
                        setAssemblyOptions(prev => ({ ...prev, subtitle_position: value }))
                      }
                    >
                      <SelectTrigger id="subtitle-position">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="top">Top</SelectItem>
                        <SelectItem value="center">Center</SelectItem>
                        <SelectItem value="bottom">Bottom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="subtitle-size">Font Size</Label>
                    <input
                      id="subtitle-size"
                      type="number"
                      min="24"
                      max="72"
                      step="4"
                      value={assemblyOptions.subtitle_font_size}
                      onChange={(e) => 
                        setAssemblyOptions(prev => ({ 
                          ...prev, 
                          subtitle_font_size: parseInt(e.target.value) 
                        }))
                      }
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="border-t pt-4" />
            
            {/* Platform Optimization */}
            <div className="space-y-3">
              <div>
                <Label htmlFor="platform" className="text-base font-semibold">Optimize for Platform</Label>
                <p className="text-sm text-muted-foreground mb-3">Adjust resolution and format for best results</p>
              </div>
              
              <Select
                value={assemblyOptions.optimize_platform}
                onValueChange={(value) => 
                  setAssemblyOptions(prev => ({ ...prev, optimize_platform: value }))
                }
              >
                <SelectTrigger id="platform">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="youtube">
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4" />
                      YouTube (1920x1080, 16:9)
                    </div>
                  </SelectItem>
                  <SelectItem value="tiktok">
                    <div className="flex items-center gap-2">
                      <Film className="w-4 h-4" />
                      TikTok (1080x1920, 9:16)
                    </div>
                  </SelectItem>
                  <SelectItem value="instagram">
                    <div className="flex items-center gap-2">
                      <Film className="w-4 h-4" />
                      Instagram Reels (1080x1920, 9:16)
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssemblyDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => {
                setShowAssemblyDialog(false);
                handleStartAssembly();
              }}
              className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white"
            >
              <Clapperboard className="w-4 h-4 mr-2" />
              {assemblyStatus === 'completed' ? 'Regenerate Video' : 'Start Assembly'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
