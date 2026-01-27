'use client';

import { GraduationCap, BookOpen, Shield, Calendar, Loader2, CheckCircle } from 'lucide-react';

interface AgentStatusProps {
  activeAgents: string[];
  completedAgents: string[];
}

const agents = [
  {
    id: 'programs_requirements',
    name: 'Programs',
    description: 'Degree requirements',
    icon: GraduationCap,
    color: 'blue',
  },
  {
    id: 'course_scheduling',
    name: 'Courses',
    description: 'Course offerings',
    icon: BookOpen,
    color: 'green',
  },
  {
    id: 'policy_compliance',
    name: 'Policy',
    description: 'University policies',
    icon: Shield,
    color: 'purple',
  },
  {
    id: 'academic_planning',
    name: 'Planning',
    description: 'Academic plans',
    icon: Calendar,
    color: 'orange',
  },
];

const colorClasses: Record<string, { bg: string; border: string; text: string }> = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
  orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' },
};

export default function AgentStatus({ activeAgents, completedAgents }: AgentStatusProps) {
  if (activeAgents.length === 0 && completedAgents.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-lg mb-4">
      <span className="text-sm text-gray-500 w-full mb-1">Agents working on your request:</span>
      {agents.map((agent) => {
        const isActive = activeAgents.includes(agent.id);
        const isComplete = completedAgents.includes(agent.id);
        const colors = colorClasses[agent.color];
        const Icon = agent.icon;

        if (!isActive && !isComplete) {
          return (
            <div
              key={agent.id}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 bg-white opacity-40"
            >
              <Icon className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">{agent.name}</span>
            </div>
          );
        }

        return (
          <div
            key={agent.id}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${colors.bg} ${colors.border} ${
              isActive ? 'agent-thinking' : ''
            }`}
          >
            <Icon className={`w-4 h-4 ${colors.text}`} />
            <span className={`text-sm font-medium ${colors.text}`}>{agent.name}</span>
            {isActive && <Loader2 className={`w-3 h-3 animate-spin ${colors.text}`} />}
            {isComplete && <CheckCircle className={`w-3 h-3 ${colors.text}`} />}
          </div>
        );
      })}
    </div>
  );
}
