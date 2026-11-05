import React, { useState } from 'react';
import { Calendar, AlertTriangle, CheckCircle2, Clock, User, Plus, Check } from 'lucide-react';
import { FullEventPlan, TimelineTask } from '../types';

interface TimelineTabProps {
  plan: FullEventPlan;
  onUpdatePlan: (updatedPlan: FullEventPlan) => void;
}

export const TimelineTab: React.FC<TimelineTabProps> = ({ plan, onUpdatePlan }) => {
  const [filterOwner, setFilterOwner] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDate, setNewDate] = useState(plan.intake.date);
  const [newOwner, setNewOwner] = useState<'user' | 'vendor' | 'helper'>('user');
  const [newPriority, setNewPriority] = useState<'high' | 'medium' | 'low'>('medium');

  const timeline = plan.timeline;
  const milestones = timeline.milestones;
  const runOfShow = timeline.run_of_show;

  const handleToggleTaskStatus = (task: TimelineTask) => {
    const nextStatus = task.status === 'completed' ? 'pending' : 'completed';
    const updated = milestones.map(t =>
      t.id === task.id ? { ...t, status: nextStatus as any } : t
    );
    onUpdatePlan({
      ...plan,
      timeline: {
        ...timeline,
        milestones: updated,
      },
    });
  };

  const handleAddTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newDate) return;

    const newTask: TimelineTask = {
      id: Math.random().toString(36).substring(2, 9),
      milestone_phase: 'Custom Added Task',
      title: newTitle,
      description: 'Added via timeline interface',
      due_date: newDate,
      owner: newOwner,
      priority: newPriority,
      status: 'pending',
      is_high_risk: false,
      is_past_due: new Date(newDate) < new Date(),
    };

    const updated = [...milestones, newTask].sort((a, b) => a.due_date.localeCompare(b.due_date));
    onUpdatePlan({
      ...plan,
      timeline: {
        ...timeline,
        milestones: updated,
      },
    });

    setNewTitle('');
    setShowAddTask(false);
  };

  // Filter tasks
  const filteredTasks = milestones.filter(t => {
    if (filterOwner !== 'all' && t.owner !== filterOwner) return false;
    if (filterStatus !== 'all' && t.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Lead-Time & Compression Alert */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">Milestone Schedule & Adaptive Timeline</h3>
            {timeline.is_compressed ? (
              <span className="px-2.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200 rounded-full flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-600" />
                Compressed Sprint (&lt; 30 Days)
              </span>
            ) : (
              <span className="px-2.5 py-0.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full">
                Standard Planning Window
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Lead time: <span className="font-semibold text-slate-700">{timeline.lead_time_days} days</span> until {plan.intake.date}. Milestones are chronologically ordered and clamped.
          </p>
        </div>

        {/* Add Task Button */}
        <button
          onClick={() => setShowAddTask(true)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Milestone Task</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-100/60 p-2.5 rounded-xl border border-slate-200">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
          <span>Filter Owner:</span>
          <select
            value={filterOwner}
            onChange={e => setFilterOwner(e.target.value)}
            className="px-2.5 py-1 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-700 focus:outline-none"
          >
            <option value="all">All Owners</option>
            <option value="user">User (You)</option>
            <option value="vendor">Vendor</option>
            <option value="helper">Helper / Coordinator</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
          <span>Status:</span>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="px-2.5 py-1 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-700 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {/* Milestones List */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs divide-y divide-slate-100 overflow-hidden">
        {filteredTasks.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No milestones match your selected filters.
          </div>
        ) : (
          filteredTasks.map((task) => {
            const isCompleted = task.status === 'completed';
            const prioColor =
              task.priority === 'high'
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : task.priority === 'medium'
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-slate-50 text-slate-600 border-slate-200';

            return (
              <div
                key={task.id}
                className={`p-4 flex items-start sm:items-center justify-between gap-4 transition-colors ${
                  isCompleted ? 'bg-slate-50/60 opacity-70' : 'hover:bg-indigo-50/20'
                }`}
              >
                <div className="flex items-start sm:items-center gap-3.5 flex-1 min-w-0">
                  {/* Status checkbox */}
                  <button
                    onClick={() => handleToggleTaskStatus(task)}
                    className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors mt-0.5 sm:mt-0 ${
                      isCompleted
                        ? 'bg-indigo-600 border-indigo-600 text-white'
                        : 'border-slate-300 hover:border-indigo-500 bg-white'
                    }`}
                  >
                    {isCompleted && <Check className="w-3.5 h-3.5" />}
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-2xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                        {task.milestone_phase}
                      </span>
                      <h4 className={`text-sm font-semibold truncate ${isCompleted ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                        {task.title}
                      </h4>
                      {task.is_high_risk && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-2xs font-bold bg-rose-100 text-rose-700 rounded-full">
                          <AlertTriangle className="w-3 h-3" /> HIGH RISK
                        </span>
                      )}
                      {task.is_past_due && !isCompleted && (
                        <span className="px-2 py-0.5 text-2xs font-bold bg-amber-100 text-amber-800 rounded-full">
                          PAST DUE
                        </span>
                      )}
                    </div>
                    {task.description && (
                      <p className="text-xs text-slate-500 mt-1 truncate">{task.description}</p>
                    )}
                  </div>
                </div>

                {/* Right Metadata */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className={`px-2 py-0.5 text-2xs font-semibold rounded-full border uppercase ${prioColor}`}>
                    {task.priority}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-slate-600 bg-slate-100 px-2 py-1 rounded-md">
                    <User className="w-3.5 h-3.5 text-slate-400" />
                    <span className="capitalize">{task.owner}</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md">
                    <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                    <span>{task.due_date}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Day-of Hourly Run of Show Schedule */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">Day-of Hourly Run-of-Show</h4>
          </div>
          <span className="text-xs text-slate-500 font-medium">{runOfShow.length} Sequential Segments</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 text-xs text-slate-500 uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 font-semibold">Time Window</th>
                <th className="px-5 py-3 font-semibold">Activity & Milestones</th>
                <th className="px-5 py-3 font-semibold">Lead Coordinator</th>
                <th className="px-5 py-3 font-semibold">Location</th>
                <th className="px-5 py-3 font-semibold">Operational Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {runOfShow.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-3 font-semibold text-indigo-700 text-xs whitespace-nowrap">
                    {item.time_slot}
                  </td>
                  <td className="px-5 py-3 font-medium text-slate-900 text-xs">
                    {item.activity}
                  </td>
                  <td className="px-5 py-3 text-slate-600 text-xs">
                    {item.lead_person}
                  </td>
                  <td className="px-5 py-3 text-slate-600 text-xs">
                    {item.location}
                  </td>
                  <td className="px-5 py-3 text-slate-400 text-xs max-w-xs truncate">
                    {item.notes || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Task Modal */}
      {showAddTask && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <h4 className="text-base font-bold text-slate-900">Add Custom Milestone Task</h4>
            <form onSubmit={handleAddTask} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Task Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  placeholder="e.g. Confirm floral centerpiece delivery"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Due Date *</label>
                  <input
                    type="date"
                    required
                    value={newDate}
                    max={plan.intake.date}
                    onChange={e => setNewDate(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Owner</label>
                  <select
                    value={newOwner}
                    onChange={e => setNewOwner(e.target.value as any)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="user">User (You)</option>
                    <option value="vendor">Vendor</option>
                    <option value="helper">Helper</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Priority</label>
                <select
                  value={newPriority}
                  onChange={e => setNewPriority(e.target.value as any)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddTask(false)}
                  className="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs"
                >
                  Add Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
