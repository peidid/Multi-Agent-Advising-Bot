'use client';

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  GraduationCap,
  BookOpen,
  Shield,
  Calendar,
  Clock,
  Zap,
  AlertTriangle,
  FileText,
  CheckCircle,
  Brain,
  TrendingUp,
} from 'lucide-react';

interface AgentDetail {
  answer: string;
  confidence: number;
  risks: Array<{ type: string; severity: string; description: string }>;
  relevant_policies: string[];
}

interface EvaluationRound {
  round: number;
  sufficient: boolean;
  quality_score: number;
  agents_to_rerun: string[];
  agent_feedback: Record<string, {
    score: number;
    strengths: string[];
    gaps: string[];
    guidance: string;
  }>;
  reasoning: string;
  eval_time: number;
}

interface WorkflowDetailsProps {
  agentsUsed: string[];
  agentDetails: Record<string, AgentDetail>;
  executionStats?: {
    execution_mode?: string;
    total_execution_time?: number;
    parallel_speedup?: number;
    final_quality_score?: number;
    evaluation_rounds?: number;
    evaluation_history?: EvaluationRound[];
  };
  phaseTiming?: Record<string, number>;
  streamEvents?: Array<{ type: string; agent?: string; message?: string; data?: Record<string, unknown> }>;
}

const agentMeta: Record<string, { name: string; icon: React.ElementType; color: string; bgColor: string }> = {
  programs_requirements: {
    name: 'Programs & Requirements',
    icon: GraduationCap,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 border-blue-200',
  },
  course_scheduling: {
    name: 'Course & Scheduling',
    icon: BookOpen,
    color: 'text-green-600',
    bgColor: 'bg-green-50 border-green-200',
  },
  policy_compliance: {
    name: 'Policy & Compliance',
    icon: Shield,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 border-purple-200',
  },
  academic_planning: {
    name: 'Academic Planning',
    icon: Calendar,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 border-orange-200',
  },
};

export default function WorkflowDetails({
  agentsUsed,
  agentDetails,
  executionStats,
  phaseTiming,
  streamEvents = [],
}: WorkflowDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>({});

  const toggleAgent = (agentId: string) => {
    setExpandedAgents((prev) => ({
      ...prev,
      [agentId]: !prev[agentId],
    }));
  };

  const totalTime = phaseTiming?.total || executionStats?.total_execution_time || 0;

  return (
    <div className="mt-3 border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <Zap className="w-4 h-4 text-cmu-red" />
          </div>
          <span className="text-sm font-medium text-gray-700">
            Workflow Details
          </span>
          <span className="text-xs text-gray-500">
            ({agentsUsed.length} agents, {totalTime.toFixed(1)}s)
          </span>
        </div>

        {/* Quick stats badges */}
        <div className="flex items-center gap-2">
          {agentsUsed.map((agentId) => {
            const meta = agentMeta[agentId];
            if (!meta) return null;
            const Icon = meta.icon;
            return (
              <div
                key={agentId}
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${meta.bgColor} border`}
                title={meta.name}
              >
                <Icon className={`w-3 h-3 ${meta.color}`} />
                <CheckCircle className={`w-3 h-3 ${meta.color}`} />
              </div>
            );
          })}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-gray-200">
          {/* Execution stats */}
          {(executionStats || phaseTiming) && (
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-4 text-xs text-gray-600">
                <div className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Total: {totalTime.toFixed(2)}s</span>
                </div>
                {executionStats?.parallel_speedup && executionStats.parallel_speedup > 1 && (
                  <div className="flex items-center gap-1 text-green-600">
                    <Zap className="w-3.5 h-3.5" />
                    <span>{executionStats.parallel_speedup.toFixed(1)}x speedup</span>
                  </div>
                )}
                {executionStats?.final_quality_score !== undefined && (
                  <div className="flex items-center gap-1 text-indigo-600">
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>Quality: {executionStats.final_quality_score}/100</span>
                  </div>
                )}
                {phaseTiming?.intent_classification && (
                  <span>Intent: {phaseTiming.intent_classification.toFixed(2)}s</span>
                )}
                {phaseTiming?.synthesis && (
                  <span>Synthesis: {phaseTiming.synthesis.toFixed(2)}s</span>
                )}
              </div>
            </div>
          )}

          {/* Coordinator Evaluation History */}
          {executionStats?.evaluation_history && executionStats.evaluation_history.length > 0 && (
            <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-indigo-600" />
                <span className="text-xs font-medium text-indigo-700">
                  Coordinator Evaluation ({executionStats.evaluation_rounds} round{executionStats.evaluation_rounds !== 1 ? 's' : ''})
                </span>
              </div>
              <div className="space-y-2">
                {executionStats.evaluation_history.map((evalRound) => (
                  <div key={evalRound.round} className="text-xs p-2 bg-white rounded border border-indigo-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-700">Round {evalRound.round}</span>
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded ${
                          evalRound.quality_score >= 75
                            ? 'bg-green-100 text-green-700'
                            : evalRound.quality_score >= 60
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {evalRound.quality_score}/100
                        </span>
                        <span className={`px-1.5 py-0.5 rounded ${
                          evalRound.sufficient
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {evalRound.sufficient ? 'Sufficient' : 'Need more'}
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-600 text-xs">{evalRound.reasoning}</p>
                    {evalRound.agent_feedback && Object.keys(evalRound.agent_feedback).length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {Object.entries(evalRound.agent_feedback).map(([agentId, fb]) => (
                          <span
                            key={agentId}
                            className={`px-1.5 py-0.5 rounded text-xs ${
                              fb.score >= 75
                                ? 'bg-green-50 text-green-700'
                                : fb.score >= 60
                                ? 'bg-yellow-50 text-yellow-700'
                                : 'bg-red-50 text-red-700'
                            }`}
                            title={fb.gaps?.join(', ') || 'No gaps'}
                          >
                            {agentMeta[agentId]?.name.split(' ')[0] || agentId}: {fb.score}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent details */}
          <div className="divide-y divide-gray-100">
            {agentsUsed.map((agentId) => {
              const meta = agentMeta[agentId];
              const detail = agentDetails[agentId];
              if (!meta) return null;

              const Icon = meta.icon;
              const isAgentExpanded = expandedAgents[agentId];

              return (
                <div key={agentId} className="bg-white">
                  {/* Agent header */}
                  <button
                    onClick={() => toggleAgent(agentId)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {isAgentExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                      <div className={`p-1.5 rounded-lg ${meta.bgColor} border`}>
                        <Icon className={`w-4 h-4 ${meta.color}`} />
                      </div>
                      <span className="text-sm font-medium text-gray-700">{meta.name}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {detail?.confidence && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          detail.confidence >= 0.8
                            ? 'bg-green-100 text-green-700'
                            : detail.confidence >= 0.6
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {Math.round(detail.confidence * 100)}% confidence
                        </span>
                      )}
                      {detail?.risks && detail.risks.length > 0 && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          {detail.risks.length} risks
                        </span>
                      )}
                    </div>
                  </button>

                  {/* Agent expanded content */}
                  {isAgentExpanded && detail && (
                    <div className="px-4 pb-4 pl-12">
                      {/* Agent answer */}
                      <div className="mb-3">
                        <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                          <FileText className="w-3.5 h-3.5" />
                          Agent Response
                        </div>
                        <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 border border-gray-200 max-h-48 overflow-y-auto">
                          <pre className="whitespace-pre-wrap font-sans">{detail.answer}</pre>
                        </div>
                      </div>

                      {/* Risks */}
                      {detail.risks && detail.risks.length > 0 && (
                        <div className="mb-3">
                          <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Identified Risks
                          </div>
                          <div className="space-y-1.5">
                            {detail.risks.map((risk, idx) => (
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
                      {detail.relevant_policies && detail.relevant_policies.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 mb-1.5">
                            <Shield className="w-3.5 h-3.5" />
                            Referenced Policies
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {detail.relevant_policies.map((policy, idx) => (
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

          {/* Event log (collapsed by default) */}
          {streamEvents.length > 0 && (
            <details className="border-t border-gray-200">
              <summary className="px-4 py-2 text-xs text-gray-500 cursor-pointer hover:bg-gray-50">
                View event log ({streamEvents.length} events)
              </summary>
              <div className="px-4 pb-3 max-h-32 overflow-y-auto">
                <div className="space-y-1">
                  {streamEvents.map((event, idx) => (
                    <div key={idx} className="text-xs text-gray-500 flex gap-2">
                      <span className="text-gray-400 font-mono">{String(idx + 1).padStart(2, '0')}</span>
                      <span className="text-gray-600">{event.type}</span>
                      {event.agent && (
                        <span className="text-blue-600">[{event.agent}]</span>
                      )}
                      {event.message && (
                        <span className="text-gray-500 truncate">{event.message}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
