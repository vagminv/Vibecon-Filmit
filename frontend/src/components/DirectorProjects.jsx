import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { 
  Film, Plus, ChevronRight, Clock, CheckCircle, Trash2, Eye
} from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { UserMenu } from './UserMenu';

export const DirectorProjects = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      // For now, load from localStorage
      // In production, this would be an API call
      const storedProjects = JSON.parse(localStorage.getItem('director_projects') || '[]');
      setProjects(storedProjects);
    } catch (error) {
      console.error('Error loading projects:', error);
      toast.error('Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  const getProjectStatus = (project) => {
    if (project.current_step === 'complete') return 'completed';
    if (project.current_step === 'video_edited') return 'editing';
    if (project.current_step === 'segments_uploaded') return 'editing';
    if (project.current_step === 'script_planned') return 'recording';
    return 'planning';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-500/10 text-green-600 border-green-500/20';
      case 'editing': return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
      case 'recording': return 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20';
      case 'planning': return 'bg-purple-500/10 text-purple-600 border-purple-500/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'editing': return <Film className="w-4 h-4" />;
      case 'recording': return <Clock className="w-4 h-4" />;
      case 'planning': return <Eye className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  const deleteProject = (projectId) => {
    const confirmed = window.confirm('Are you sure you want to delete this project?');
    if (confirmed) {
      const updatedProjects = projects.filter(p => p.project_id !== projectId);
      localStorage.setItem('director_projects', JSON.stringify(updatedProjects));
      setProjects(updatedProjects);
      toast.success('Project deleted');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-sky">
      {/* Navigation */}
      <nav className="border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <button onClick={() => navigate('/')} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <span className="text-5xl font-logo font-bold text-foreground">filmit!</span>
            </button>
            <div className="flex items-center gap-4">
              <Badge className="bg-primary/20 text-primary border-primary/30 font-sans">
                <Film className="w-3 h-3 mr-1" />
                My Projects
              </Badge>
              <UserMenu />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-8">
          
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-display font-bold text-foreground">My Projects</h1>
              <p className="text-muted-foreground mt-2">Manage all your video projects in one place</p>
            </div>
            <Button
              onClick={() => navigate('/director')}
              className="bg-gradient-primary hover:shadow-glow transition-all duration-300"
              size="lg"
            >
              <Plus className="w-5 h-5 mr-2" />
              New Project
            </Button>
          </div>

          {/* Projects Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto animate-pulse">
                  <Film className="w-8 h-8 text-primary" />
                </div>
                <p className="text-muted-foreground">Loading projects...</p>
              </div>
            </div>
          ) : projects.length === 0 ? (
            <Card className="border-dashed border-2 border-border/50">
              <CardContent className="py-20">
                <div className="text-center space-y-4">
                  <div className="w-20 h-20 rounded-2xl bg-muted flex items-center justify-center mx-auto">
                    <Film className="w-10 h-10 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">No projects yet</h3>
                    <p className="text-muted-foreground mb-6">Start your first video project with AI Director</p>
                    <Button
                      onClick={() => navigate('/director')}
                      className="bg-gradient-primary hover:shadow-glow"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Create First Project
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((project) => {
                const status = getProjectStatus(project);
                return (
                  <Card 
                    key={project.project_id}
                    className="border-border/50 hover:shadow-xl transition-all duration-300 cursor-pointer group"
                    onClick={() => navigate(`/director/studio/${project.project_id}`)}
                  >
                    <CardContent className="pt-6 pb-6">
                      <div className="space-y-4">
                        {/* Status Badge */}
                        <div className="flex items-center justify-between">
                          <Badge className={`${getStatusColor(status)} capitalize`}>
                            {getStatusIcon(status)}
                            <span className="ml-1.5">{status}</span>
                          </Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteProject(project.project_id);
                            }}
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>

                        {/* Project Goal */}
                        <div>
                          <h3 className="font-semibold text-foreground line-clamp-2 mb-2">
                            {project.user_goal}
                          </h3>
                          {project.matched_format && (
                            <p className="text-xs text-muted-foreground">
                              Format: {project.matched_format.name}
                            </p>
                          )}
                        </div>

                        {/* Progress */}
                        {project.shot_list && (
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-muted-foreground">Progress</span>
                              <span className="font-semibold text-foreground">
                                {project.shot_list.filter(s => s.uploaded).length} / {project.shot_list.length}
                              </span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-gradient-primary transition-all duration-300"
                                style={{ 
                                  width: `${(project.shot_list.filter(s => s.uploaded).length / project.shot_list.length) * 100}%` 
                                }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Metadata */}
                        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
                          <span>{project.target_platform || 'TikTok'}</span>
                          <span className="flex items-center gap-1">
                            <ChevronRight className="w-4 h-4" />
                            Open
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
