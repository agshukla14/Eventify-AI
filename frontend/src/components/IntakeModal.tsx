import React, { useState } from 'react';
import { X, Sparkles, Heart, Gift, Users, Calendar, MapPin, DollarSign, Wand2 } from 'lucide-react';
import { EventIntake, EventType } from '../types';

interface IntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (intake: EventIntake) => Promise<void>;
  isLoading: boolean;
}

const DIETARY_OPTIONS = [
  'Vegetarian',
  'Strict Jain (No root veg)',
  '100% Vegan',
  'Halal',
  'Gluten-Free',
  'Nut-Free',
  'Kosher',
];

export const IntakeModal: React.FC<IntakeModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}) => {
  const [eventType, setEventType] = useState<EventType>('wedding');
  const [title, setTitle] = useState('');
  const [date, setDate] = useState('');
  const [city, setCity] = useState('');
  const [guestCount, setGuestCount] = useState<number>(150);
  const [totalBudget, setTotalBudget] = useState<number>(1000000);
  const [currency, setCurrency] = useState('INR');
  const [themeStyle, setThemeStyle] = useState('');
  const [culturalPrefs, setCulturalPrefs] = useState('');
  const [selectedDiets, setSelectedDiets] = useState<string[]>([]);
  const [mustHaves, setMustHaves] = useState('');
  const [ageGroup, setAgeGroup] = useState('');

  if (!isOpen) return null;

  const toggleDiet = (diet: string) => {
    setSelectedDiets(prev =>
      prev.includes(diet) ? prev.filter(d => d !== diet) : [...prev, diet]
    );
  };

  const handlePreset = (type: EventType) => {
    setEventType(type);
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + (type === 'wedding' ? 180 : type === 'birthday' ? 30 : 60));
    const dateStr = futureDate.toISOString().split('T')[0];
    setDate(dateStr);

    if (type === 'wedding') {
      setTitle('Priya & Rohan Royal Palace Wedding');
      setCity('Jaipur');
      setGuestCount(350);
      setTotalBudget(2500000);
      setCurrency('INR');
      setThemeStyle('Royal Rajasthani Heritage & Marigolds');
      setCulturalPrefs('Traditional Hindu Vedic Rituals & Sangeet Gala');
      setSelectedDiets(['Vegetarian']);
      setMustHaves('Vintage car grand baraat, Live shehnai, Floral mandap arch');
      setAgeGroup('Multi-generational families, elders, and young friends');
    } else if (type === 'birthday') {
      setTitle("Leo's 10th Superhero Academy Party");
      setCity('Bengaluru');
      setGuestCount(45);
      setTotalBudget(65000);
      setCurrency('INR');
      setThemeStyle('Avengers Superhero Training Camp');
      setCulturalPrefs('Fun interactive milestone party');
      setSelectedDiets(['Vegetarian', 'Nut-Free']);
      setMustHaves('Custom Spider-Man 3D Cake, Obstacle course, Goodie bags');
      setAgeGroup('Kids aged 9-11 and parents');
    } else {
      setTitle('Indiranagar Community Green Tech Mela');
      setCity('Bengaluru');
      setGuestCount(500);
      setTotalBudget(600000);
      setCurrency('INR');
      setThemeStyle('Eco-Innovation & Solar Futures');
      setCulturalPrefs('Open neighborhood civic festival');
      setSelectedDiets(['Vegetarian']);
      setMustHaves('Keynote AV stage, Solar power station, Waste segregation team');
      setAgeGroup('Residents, students, and senior citizens');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !date || !city) return;

    const intake: EventIntake = {
      event_type: eventType,
      title,
      date,
      city,
      guest_count: Number(guestCount),
      total_budget: Number(totalBudget),
      currency,
      theme_style: themeStyle || undefined,
      cultural_preferences: culturalPrefs || undefined,
      dietary_preferences: selectedDiets,
      must_haves: mustHaves ? mustHaves.split(',').map(s => s.trim()).filter(Boolean) : [],
      age_group_details: ageGroup || undefined,
    };

    await onSubmit(intake);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">

        {/* Modal Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-teal-700 to-emerald-600 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/10 backdrop-blur-md">
              <Sparkles className="w-5 h-5 text-teal-200" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Create New Celebration Plan</h2>
              <p className="text-xs text-teal-100">Powered by Gemini GenAI & Deterministic Math Engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">

          {/* Quick Demo Presets */}
          <div className="bg-teal-50/60 border border-teal-200/60 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-teal-900">
              <Wand2 className="w-3.5 h-3.5 text-teal-600" />
              <span>One-Click Demo Presets:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handlePreset('wedding')}
                className="px-2.5 py-1 text-xs font-medium bg-white text-teal-800 hover:bg-teal-100 rounded-md border border-teal-300 shadow-xs transition-colors"
              >
                💍 Royal Wedding
              </button>
              <button
                type="button"
                onClick={() => handlePreset('birthday')}
                className="px-2.5 py-1 text-xs font-medium bg-white text-teal-800 hover:bg-teal-100 rounded-md border border-teal-300 shadow-xs transition-colors"
              >
                🎂 10th Birthday
              </button>
              <button
                type="button"
                onClick={() => handlePreset('community')}
                className="px-2.5 py-1 text-xs font-medium bg-white text-teal-800 hover:bg-teal-100 rounded-md border border-teal-300 shadow-xs transition-colors"
              >
                🎪 Community Mela
              </button>
            </div>
          </div>

          {/* Event Type Cards */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              1. Event Type
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { type: 'wedding', label: 'Wedding', icon: Heart, desc: 'Ceremonies, Sangeet & Reception' },
                { type: 'birthday', label: 'Birthday', icon: Gift, desc: 'Milestone & Kids Parties' },
                { type: 'community', label: 'Community', icon: Users, desc: 'Galas, Melas, Hackathons' },
              ].map(({ type, label, icon: Icon, desc }) => (
                <button
                  type="button"
                  key={type}
                  onClick={() => setEventType(type as EventType)}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    eventType === type
                      ? 'border-teal-500 bg-teal-50/50 shadow-sm ring-2 ring-teal-500/20'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <Icon className={`w-5 h-5 mb-2 ${eventType === type ? 'text-teal-600' : 'text-slate-400'}`} />
                  <div className="font-semibold text-sm text-slate-900">{label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Primary Details */}
          <div className="space-y-4">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              2. Core Details
            </label>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Event Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Maya & Aryan Wedding, Kabir's 5th Birthday"
                className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Target Date *</label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="date"
                    required
                    value={date}
                    onChange={e => setDate(e.target.value)}
                    className="w-full pl-9 pr-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">City / Location *</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={city}
                    onChange={e => setCity(e.target.value)}
                    placeholder="e.g. Mumbai, Jaipur, Bengaluru"
                    className="w-full pl-9 pr-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Guest Count *</label>
                <input
                  type="number"
                  min="1"
                  max="100000"
                  required
                  value={guestCount}
                  onChange={e => setGuestCount(Number(e.target.value))}
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Total Budget *</label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  required
                  value={totalBudget}
                  onChange={e => setTotalBudget(Number(e.target.value))}
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Currency</label>
                <select
                  value={currency}
                  onChange={e => setCurrency(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="AED">AED (د.إ)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Preferences & Aesthetics */}
          <div className="space-y-4">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              3. Themes, Culture & Dietary Constraints
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Theme / Style</label>
                <input
                  type="text"
                  value={themeStyle}
                  onChange={e => setThemeStyle(e.target.value)}
                  placeholder="e.g. Boho Chic, Royal Heritage, Vintage 80s"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Cultural / Ceremonial Traditions</label>
                <input
                  type="text"
                  value={culturalPrefs}
                  onChange={e => setCulturalPrefs(e.target.value)}
                  placeholder="e.g. Punjabi Sangeet, Vedic Muhurtham, Christian Vows"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            {/* Dietary Restrictions Multi-Select */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Dietary Constraints (Guarded)</label>
              <div className="flex flex-wrap gap-2">
                {DIETARY_OPTIONS.map(d => {
                  const isSelected = selectedDiets.includes(d);
                  return (
                    <button
                      type="button"
                      key={d}
                      onClick={() => toggleDiet(d)}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
                        isSelected
                          ? 'bg-teal-600 text-white border-teal-600 shadow-xs'
                          : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
                      }`}
                    >
                      {isSelected ? '✓ ' : '+ '}{d}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Must-Haves (Comma separated)</label>
                <input
                  type="text"
                  value={mustHaves}
                  onChange={e => setMustHaves(e.target.value)}
                  placeholder="e.g. Fireworks, Drone, Photo booth"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Age Group / Crowd Demographics</label>
                <input
                  type="text"
                  value={ageGroup}
                  onChange={e => setAgeGroup(e.target.value)}
                  placeholder="e.g. Kids 4-8, Teens, Multi-generational"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>
          </div>

          {/* Submit Actions */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !title || !date || !city}
              className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 rounded-lg shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Generating Complete Plan...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate AI Plan</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
