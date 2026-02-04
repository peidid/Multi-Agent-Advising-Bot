'use client';

import { GraduationCap, BookOpen, Shield, Calendar, Loader2, CheckCircle, Brain, ArrowRight } from 'lucide-react';

// Stream event type from API
interface StreamEvent {
  type: string;
  agent?: string;
  phase?: string;
  message?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

interface AgentStatusProps {
  activeAgents: string[];
  completedAgents: string[];
  streamEvents?: StreamEvent[];
  currentPhase?: string;
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

const colorClasses: Record<string, { bg: string; border: string; text: string; pulse: string }> = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', pulse: 'bg-blue-400' },
  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', pulse: 'bg-green-400' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', pulse: 'bg-purple-400' },
  orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', pulse: 'bg-orange-400' },
};

export default function AgentStatus({
  activeAgents,
  completedAgents,
  streamEvents = [],
  currentPhase = '',
}: AgentStatusProps) {
  // Get the last few events for display
  const recentEvents = streamEvents.slice(-5);

  // Find current agent messages
  const agentMessages: Record<string, string> = {};
  for (const event of streamEvents) {
    if (event.agent && event.message) {
      agentMessages[event.agent] = event.message;
    }
  }

  return (
    <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 p-4 mb-4 shadow-sm">
      {/* Current Phase Header */}
      {currentPhase && (
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
          <div className="relative">
            <Brain className="w-5 h-5 text-cmu-red" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-cmu-red rounded-full animate-ping" />
          </div>
          <span className="text-sm font-medium text-gray-700">{currentPhase}</span>
        </div>
      )}

      {/* Agent Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {agents.map((agent) => {
          const isActive = activeAgents.includes(agent.id);
          const isComplete = completedAgents.includes(agent.id);
          const colors = colorClasses[agent.color];
          const Icon = agent.icon;
          const statusMessage = agentMessages[agent.id];

          // Determine card state
          const isInvolved = isActive || isComplete;

          return (
            <div
              key={agent.id}
              className={`
                relative rounded-lg border p-3 transition-all duration-300
                ${isInvolved
                  ? `${colors.bg} ${colors.border} shadow-sm`
                  : 'bg-white border-gray-200 opacity-50'
                }
                ${isActive ? 'ring-2 ring-offset-1 ring-blue-300' : ''}
              `}
            >
              {/* Active indicator pulse */}
              {isActive && (
                <span className={`absolute top-2 right-2 w-2 h-2 ${colors.pulse} rounded-full animate-ping`} />
              )}

              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-4 h-4 ${isInvolved ? colors.text : 'text-gray-400'}`} />
                <span className={`text-sm font-medium ${isInvolved ? colors.text : 'text-gray-400'}`}>
                  {agent.name}
                </span>
                {isActive && <Loader2 className={`w-3 h-3 animate-spin ${colors.text}`} />}
                {isComplete && <CheckCircle className={`w-3 h-3 ${colors.text}`} />}
              </div>

              {/* Status message */}
              {isInvolved && statusMessage && (
                <p className={`text-xs ${colors.text} opacity-80 truncate`} title={statusMessage}>
                  {statusMessage}
                </p>
              )}

              {!isInvolved && (
                <p className="text-xs text-gray-400">{agent.description}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Event Stream (shows recent activity) */}
      {recentEvents.length > 0 && (
        <div className="border-t border-gray-200 pt-3">
          <div className="space-y-1.5">
            {recentEvents.map((event, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-xs text-gray-600 animate-fadeIn"
              >
                <ArrowRight className="w-3 h-3 mt-0.5 text-gray-400 flex-shrink-0" />
                <span>
                  {event.agent && (
                    <span className="font-medium text-gray-700">
                      {agents.find((a) => a.id === event.agent)?.name || event.agent}:
                    </span>
                  )}{' '}
                  {event.message || event.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
