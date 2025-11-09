import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, User, Settings, Film, FolderOpen } from 'lucide-react';

export const UserMenu = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="relative">
      {/* User Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-semibold">
          {user.username.charAt(0).toUpperCase()}
        </div>
        <div className="hidden md:block text-left">
          <div className="text-sm font-semibold text-foreground">{user.username}</div>
          <div className="text-xs text-muted-foreground">Studio</div>
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-lg shadow-xl z-50 overflow-hidden">
            {/* User Info Header */}
            <div className="px-4 py-3 bg-gradient-to-br from-primary/10 to-secondary/10 border-b border-border">
              <div className="text-sm font-semibold text-foreground">{user.username}</div>
              <div className="text-xs text-muted-foreground">{user.email}</div>
            </div>

            {/* Menu Items */}
            <div className="py-2">
              <button
                onClick={() => {
                  navigate('/director');
                  setIsOpen(false);
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-primary/5 transition-colors flex items-center gap-2"
              >
                <Film className="w-4 h-4" />
                Director Home
              </button>
              
              <button
                onClick={() => {
                  navigate('/director/projects');
                  setIsOpen(false);
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-primary/5 transition-colors flex items-center gap-2"
              >
                <FolderOpen className="w-4 h-4" />
                My Projects
              </button>
            </div>

            {/* Logout */}
            <div className="border-t border-border py-2">
              <button
                onClick={handleLogout}
                className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
