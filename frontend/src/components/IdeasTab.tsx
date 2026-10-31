import React, { useState } from 'react';
import { Sparkles, Utensils, Palette, Music, PartyPopper, Gift, Tag, DollarSign, Lightbulb } from 'lucide-react';
import { FullEventPlan, PersonalizedIdeaItem } from '../types';

interface IdeasTabProps {
  plan: FullEventPlan;
}

export const IdeasTab: React.FC<IdeasTabProps> = ({ plan }) => {
  const [activeCategory, setActiveCategory] = useState<string>('all');

  const ideas = plan.ideas;

  const categories = [
    { id: 'all', label: 'All Curations', icon: Sparkles, count:
      ideas.themes.length + ideas.decor.length + ideas.food_menu.length +
      ideas.activities.length + ideas.entertainment.length + ideas.return_gifts.length
    },
    { id: 'themes', label: 'Themes', icon: Palette, items: ideas.themes },
    { id: 'decor', label: 'Decor', icon: Sparkles, items: ideas.decor },
    { id: 'food_menu', label: 'Food & Menu', icon: Utensils, items: ideas.food_menu },
    { id: 'activities', label: 'Activities', icon: PartyPopper, items: ideas.activities },
    { id: 'entertainment', label: 'Entertainment', icon: Music, items: ideas.entertainment },
    { id: 'return_gifts', label: 'Favors & Gifts', icon: Gift, items: ideas.return_gifts },
  ];

  const renderIdeaCard = (item: PersonalizedIdeaItem, catLabel: string) => (
    <div key={item.id} className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-2xs font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200/50">
            {catLabel}
          </span>
          <div className="flex flex-wrap gap-1">
            {item.tags.map((t, i) => (
              <span key={i} className="text-2xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                #{t}
              </span>
            ))}
          </div>
        </div>

        <h4 className="text-base font-bold text-slate-900">{item.title}</h4>
        <p className="text-xs text-slate-600 mt-2 leading-relaxed">{item.description}</p>

        {item.rationale && (
          <div className="mt-3 p-2.5 bg-slate-50 rounded-xl text-2xs text-slate-500 flex items-start gap-2">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
            <span><strong className="text-slate-700">Why it fits:</strong> {item.rationale}</span>
          </div>
        )}
      </div>

      {/* Prominent Budget Swap Box */}
      <div className="mt-4 pt-3.5 border-t border-slate-100">
        <div className="p-3 bg-emerald-50/70 border border-emerald-200/60 rounded-xl flex items-start gap-2.5">
          <DollarSign className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="text-2xs font-bold text-emerald-800 uppercase tracking-wide">
              Budget-Friendly Swap:
            </span>
            <p className="text-xs font-medium text-emerald-900 mt-0.5">
              {item.budget_friendly_swap}
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Personalized Ideas & Smart Budget Swaps</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Grounded in your city ({plan.intake.city}), cultural traditions, and strictly guarded dietary constraints.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {plan.intake.dietary_preferences.length > 0 && (
            <span className="px-3 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg">
              Diet Guard Active: {plan.intake.dietary_preferences.join(', ')}
            </span>
          )}
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        {categories.map(c => {
          const Icon = c.icon;
          const isActive = activeCategory === c.id;
          return (
            <button
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-teal-600 text-white shadow-sm shadow-teal-500/20'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{c.label}</span>
            </button>
          );
        })}
      </div>

      {/* Ideas Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {activeCategory === 'all' ? (
          <>
            {ideas.themes.map(t => renderIdeaCard(t, 'Theme'))}
            {ideas.decor.map(d => renderIdeaCard(d, 'Decor'))}
            {ideas.food_menu.map(f => renderIdeaCard(f, 'Food & Catering'))}
            {ideas.activities.map(a => renderIdeaCard(a, 'Activity'))}
            {ideas.entertainment.map(e => renderIdeaCard(e, 'Entertainment'))}
            {ideas.return_gifts.map(g => renderIdeaCard(g, 'Return Gift'))}
          </>
        ) : (
          categories.find(c => c.id === activeCategory)?.items?.map(it =>
            renderIdeaCard(it, categories.find(c => c.id === activeCategory)?.label || '')
          )
        )}
      </div>
    </div>
  );
};
