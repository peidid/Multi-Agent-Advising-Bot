'use client';

import { useState } from 'react';
import {
  GraduationCap,
  BookOpen,
  Shield,
  Calendar,
  Loader2,
  CheckCircle,
  Brain,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  FileText,
} from 'lucide-react';

// Stream event type from API
interface StreamEvent {
  type: string;
  agent?: string;
  phase?: string;
  message?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

interface AgentOutput {
  answer: string;
  confidence: number;
  risks: Array<{ type: string; severity: string; description: string }>;
  relevant_policies: string[];
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
    name: 'Programs & Requirements',
    shortName: 'Programs',
    description: 'Degree requirements',
    icon: GraduationCap,
    color: 'blue',
  },
  {
    id: 'course_scheduling',
    name: 'Course & Scheduling',
    shortName: 'Courses',
    description: 'Course offerings',
    icon: BookOpen,
    color: 'green',
  },
  {
    id: 'policy_compliance',
    name: 'Policy & Compliance',
    shortName: 'Policy',
    description: 'University policies',
    icon: Shield,
    color: 'purple',
  },
  {
    id: 'academic_planning',
    name: 'Academic Planning',
    shortName: 'Planning',
    description: 'Academic plans',
    icon: Calendar,
    color: 'orange',
  },
];

const colorClasses: Record<string, { bg: string; border: string; text: string; pulse: string; lightBg: string }> = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', pulse: 'bg-blue-400', lightBg: 'bg-blue-25' },
  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', pulse: 'bg-green-400', lightBg: 'bg-green-25' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', pulse: 'bg-purple-400', lightBg: 'bg-purple-25' },
  orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', pulse: 'bg-orange-400', lightBg: 'bg-orange-25' },
};

export default function AgentStatus({
  activeAgents,
  completedAgents,
  streamEvents = [],
  currentPhase = '',
}: AgentStatusProps) {
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>({});

  // Get the last few events for display
  const recentEvents = streamEvents.slice(-5);

  // Find current agent messages
  const agentMessages: Record<string, string> = {};
  for (const event of streamEvents) {
    if (event.agent && event.message) {
      agentMessages[event.agent] = event.message;
    }
  }

  // Extract agent outputs from stream events
  const agentOutputs: Record<string, AgentOutput> = {};
  for (const event of streamEvents) {
    if (event.type === 'agent_output' && event.agent && event.data) {
      agentOutputs[event.agent] = event.data as unknown as AgentOutput;
    }
  }

  const toggleAgent = (agentId: string) => {
    setExpandedAgents((prev) => ({
      ...prev,
      [agentId]: !prev[agentId],
    }));
  };

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
      <div className="space-y-3 mb-4">
        {agents.map((agent) => {
          const isActive = activeAgents.includes(agent.id);
          const isComplete = completedAgents.includes(agent.id);
          const colors = colorClasses[agent.color];
          const Icon = agent.icon;
          const statusMessage = agentMessages[agent.id];
          const output = agentOutputs[agent.id];
          const isExpanded = expandedAgents[agent.id];

          // Determine card state
          const isInvolved = isActive || isComplete;
          const hasOutput = !!output;

          if (!isInvolved) return null;

          return (
            <div
              key={agent.id}
              className={`rounded-lg border transition-all duration-300 ${colors.bg} ${colors.border} shadow-sm overflow-hidden`}
            >
              {/* Agent Header */}
              <button
                onClick={() => hasOutput && toggleAgent(agent.id)}
                className={`w-full px-3 py-2.5 flex items-center justify-between ${hasOutput ? 'cursor-pointer hover:bg-white/30' : 'cursor-default'}`}
                disabled={!hasOutput}
              >
                <div className="flex items-center gap-2">
                  {hasOutput ? (
                    isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )
                  ) : (
                    <div className="w-4 h-4" />
                  )}
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                  <span className={`text-sm font-medium ${colors.text}`}>
                    {agent.shortName}
                  </span>
                  {isActive && <Loader2 className={`w-3 h-3 animate-spin ${colors.text}`} />}
                  {isComplete && <CheckCircle className={`w-3 h-3 ${colors.text}`} />}
                </div>

                <div className="flex items-center gap-2">
                  {/* Status message or confidence badge */}
                  {hasOutput ? (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      output.confidence >= 0.8
                        ? 'bg-green-100 text-green-700'
                        : output.confidence >= 0.6
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {Math.round(output.confidence * 100)}% confidence
                    </span>
                  ) : (
                    statusMessage && (
                      <span className={`text-xs ${colors.text} opacity-80`}>
                        {statusMessage}
                      </span>
                    )
                  )}
                  {output?.risks && output.risks.length > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {output.risks.length}
                    </span>
                  )}
                </div>
              </button>

              {/* Expanded Agent Output */}
              {isExpanded && output && (
                <div className="px-4 pb-3 border-t border-gray-200/50 bg-white/40">
                  {/* Agent Response */}
                  <div className="mt-3">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                      <FileText className="w-3.5 h-3.5" />
                      Agent Response
                    </div>
                    <div className="text-sm text-gray-700 bg-white rounded-lg p-3 border border-gray-200 max-h-40 overflow-y-auto">
                      <pre className="whitespace-pre-wrap font-sans">{output.answer}</pre>
                    </div>
                  </div>

                  {/* Risks */}
                  {output.risks && output.risks.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Identified Risks
                      </div>
                      <div className="space-y-1.5">
                        {output.risks.map((risk, idx) => (
                          <div
                            key={idx}
                            className={`text-xs p-2 rounded-lg border ${
                              risk.severity === 'high'
                                ? 'bg-red-50 border-red-200 text-red-800'
                                : risk.severity === 'medium'
                                ? 'bg-orange-50 border-orange-200 text-orange-800'
                                : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                            }`}
                          >
                            <span className="font-medium">{risk.type}</span>: {risk.description}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Policies */}
                  {output.relevant_policies && output.relevant_policies.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                        <Shield className="w-3.5 h-3.5" />
                        Referenced Policies
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {output.relevant_policies.map((policy, idx) => (
                          <span
                            key={idx}
                            className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-md"
                          >
                            {policy}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
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
                      {agents.find((a) => a.id === event.agent)?.shortName || event.agent}:
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
