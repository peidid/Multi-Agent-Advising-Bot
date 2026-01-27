'use client';

import { useState, useEffect } from 'react';
import { X, Loader2, Save } from 'lucide-react';
import { auth, UserProfile } from '@/lib/api';

interface ProfileModalProps {
  profile?: UserProfile;
  onClose: () => void;
  onSave: (profile: UserProfile) => void;
}

export default function ProfileModal({ profile, onClose, onSave }: ProfileModalProps) {
  const [major, setMajor] = useState(profile?.major || '');
  const [minors, setMinors] = useState(profile?.minors?.join(', ') || '');
  const [gpa, setGpa] = useState(profile?.gpa?.toString() || '');
  const [courses, setCourses] = useState(profile?.completed_courses?.join(', ') || '');
  const [interests, setInterests] = useState(profile?.interests?.join(', ') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const profileData: UserProfile = {
      major: major || undefined,
      minors: minors ? minors.split(',').map((s) => s.trim()).filter(Boolean) : [],
      gpa: gpa ? parseFloat(gpa) : undefined,
      completed_courses: courses ? courses.split(',').map((s) => s.trim()).filter(Boolean) : [],
      interests: interests ? interests.split(',').map((s) => s.trim()).filter(Boolean) : [],
    };

    try {
      await auth.updateProfile(profileData);
      onSave(profileData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-lg mx-4 overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-cmu-red text-white p-6 relative flex-shrink-0">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 hover:bg-white/20 rounded"
          >
            <X className="w-5 h-5" />
          </button>
          <h2 className="text-2xl font-bold">Academic Profile</h2>
          <p className="text-white/80 mt-1">
            Help us personalize your advising experience
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Primary Major
            </label>
            <select
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
            >
              <option value="">Select your major</option>
              <option value="Information Systems">Information Systems</option>
              <option value="Computer Science">Computer Science</option>
              <option value="Business Administration">Business Administration</option>
              <option value="Biological Sciences">Biological Sciences</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minors (comma-separated)
            </label>
            <input
              type="text"
              value={minors}
              onChange={(e) => setMinors(e.target.value)}
              placeholder="e.g., Computer Science, Data Science"
              className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Current GPA
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="4"
              value={gpa}
              onChange={(e) => setGpa(e.target.value)}
              placeholder="e.g., 3.5"
              className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Completed Courses (comma-separated course codes)
            </label>
            <textarea
              value={courses}
              onChange={(e) => setCourses(e.target.value)}
              placeholder="e.g., 15-112, 15-122, 67-262"
              rows={3}
              className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Career Interests (comma-separated)
            </label>
            <input
              type="text"
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
              placeholder="e.g., Software Engineering, Data Science"
              className="w-full px-4 py-2 border rounded-lg focus:border-cmu-red focus:ring-1 focus:ring-cmu-red outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cmu-red text-white py-3 rounded-lg font-medium hover:bg-cmu-darkred transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Profile
          </button>
        </form>
      </div>
    </div>
  );
}
