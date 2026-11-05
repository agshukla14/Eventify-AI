import React, { useState, useEffect, useMemo } from 'react';
import {
  CloudSun,
  Sun,
  CloudRain,
  CloudLightning,
  Wind,
  Droplets,
  Thermometer,
  Calendar,
  MapPin,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  Clock,
  RefreshCw,
  Search,
  Check,
  ListPlus,
  HelpCircle,
  Sunrise,
  Sunset,
  Umbrella,
  Flame,
  Info,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  FullEventPlan,
  WeatherReportResponse,
  SmartWeatherRecommendation,
  WeatherRiskLevel,
} from '../types';
import {
  getEventWeather,
  getWeatherReport,
  askWeatherAssistant,
  saveWeatherTimelineTasks,
} from '../api';

interface WeatherPlannerTabProps {
  plan: FullEventPlan | null;
  onRefreshPlan?: () => void;
}

export const WeatherPlannerTab: React.FC<WeatherPlannerTabProps> = ({ plan, onRefreshPlan }) => {
  // Input parameters
  const [cityInput, setCityInput] = useState<string>(plan?.intake.city || 'Jaipur');
  const [dateInput, setDateInput] = useState<string>(plan?.intake.date || new Date().toISOString().split('T')[0]);

  // Weather state
  const [weatherData, setWeatherData] = useState<WeatherReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Mitigation tasks selection & modal
  const [selectedRecommendations, setSelectedRecommendations] = useState<string[]>([]);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [isSavingTasks, setIsSavingTasks] = useState<boolean>(false);
  const [timelineSaveNotice, setTimelineSaveNotice] = useState<string | null>(null);

  // AI Assistant state
  const [aiQuestion, setAiQuestion] = useState<string>('');
  const [isAiLoading, setIsAiLoading] = useState<boolean>(false);
  const [aiAnswer, setAiAnswer] = useState<{
    answer: string;
    data_grounding: string;
    is_forecast_based: boolean;
    key_suggestions: string[];
  } | null>(null);

  // Active chart view
  const [chartView, setChartView] = useState<'temp' | 'rain' | 'wind'>('temp');

  // Synchronize city and date with plan if changed
  useEffect(() => {
    if (plan) {
      setCityInput(plan.intake.city);
      setDateInput(plan.intake.date);
      loadWeather(plan.intake.city, plan.intake.date);
    } else {
      loadWeather(cityInput, dateInput);
    }
  }, [plan?.event_id]);

  const loadWeather = async (city: string, targetDate: string) => {
    setIsLoading(true);
    setFetchError(null);
    try {
      let report: WeatherReportResponse;
      if (plan?.event_id) {
        report = await getEventWeather(plan.event_id, city, targetDate);
      } else {
        report = await getWeatherReport(city, targetDate, 'wedding');
      }
      setWeatherData(report);
      // Auto-select critical recommendations by default
      const criticalIds = report.recommendations
        .filter((r) => r.priority === 'Critical')
        .map((r) => r.title);
      setSelectedRecommendations(criticalIds);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to retrieve meteorological data.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cityInput.trim()) return;
    loadWeather(cityInput, dateInput);
  };

  const handleToggleRecommendation = (title: string) => {
    setSelectedRecommendations((prev) =>
      prev.includes(title) ? prev.filter((t) => t !== title) : [...prev, title]
    );
  };

  const handleSelectAllRecommendations = () => {
    if (!weatherData) return;
    if (selectedRecommendations.length === weatherData.recommendations.length) {
      setSelectedRecommendations([]);
    } else {
      setSelectedRecommendations(weatherData.recommendations.map((r) => r.title));
    }
  };

  const handleSaveToTimeline = async () => {
    if (!plan || selectedRecommendations.length === 0) return;
    setIsSavingTasks(true);
    try {
      const res = await saveWeatherTimelineTasks(plan.event_id, {
        task_titles: selectedRecommendations,
        phase: 'Week Of Event',
        priority: 'high',
      });

      setIsConfirmModalOpen(false);
      onRefreshPlan?.();

      const addedCount = res.added_tasks.length;
      const skippedCount = res.skipped_duplicates.length;
      let msg = `Successfully added ${addedCount} mitigation task${addedCount === 1 ? '' : 's'} to your event timeline!`;
      if (skippedCount > 0) {
        msg += ` (${skippedCount} task${skippedCount === 1 ? '' : 's'} skipped as already existing).`;
      }
      setTimelineSaveNotice(msg);
      setTimeout(() => setTimelineSaveNotice(null), 6000);
    } catch (err: any) {
      alert(`Failed to save tasks: ${err.message}`);
    } finally {
      setIsSavingTasks(false);
    }
  };

  const handleAskAi = async (customPrompt?: string) => {
    const q = customPrompt || aiQuestion;
    if (!q.trim() || !weatherData) return;

    setIsAiLoading(true);
    try {
      const res = await askWeatherAssistant({
        question: q,
        event_id: plan?.event_id,
        location: weatherData.location,
        target_date: weatherData.target_date,
        event_type: plan?.intake.event_type || 'wedding',
      });
      setAiAnswer(res);
      if (!customPrompt) setAiQuestion('');
    } catch (err: any) {
      alert(`AI Assistant Error: ${err.message}`);
    } finally {
      setIsAiLoading(false);
    }
  };

  // Weather Icon Helper
  const getWeatherIcon = (code: number, sizeClass = 'w-6 h-6') => {
    if (code === 0) return <Sun className={`${sizeClass} text-amber-500`} />;
    if ([1, 2, 3].includes(code)) return <CloudSun className={`${sizeClass} text-sky-500`} />;
    if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return <CloudRain className={`${sizeClass} text-indigo-500`} />;
    if ([95, 96, 99].includes(code)) return <CloudLightning className={`${sizeClass} text-purple-600`} />;
    return <CloudSun className={`${sizeClass} text-slate-500`} />;
  };

  // Risk Badge Colors
  const getRiskBadge = (level: WeatherRiskLevel) => {
    switch (level) {
      case 'High':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-200">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
            <span>High Risk</span>
          </span>
        );
      case 'Moderate':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>Moderate Risk</span>
          </span>
        );
      case 'Low':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Low Risk</span>
          </span>
        );
    }
  };

  // Format Recharts data
  const chartData = useMemo(() => {
    if (!weatherData) return [];
    if (weatherData.daily_forecast.length > 0) {
      return weatherData.daily_forecast.map((d) => ({
        name: d.date.slice(5),
        maxTemp: Math.round(d.temp_max),
        minTemp: Math.round(d.temp_min),
        apparentTemp: Math.round(d.apparent_temp_max),
        rainProb: Math.round(d.rain_probability_max),
        precip: Number(d.precipitation_sum.toFixed(1)),
        wind: Math.round(d.wind_speed_max),
      }));
    }
    return [];
  }, [weatherData]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* 1. Header Banner */}
      <div className="bg-gradient-to-r from-sky-700 via-indigo-700 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-semibold mb-3">
            <CloudSun className="w-4 h-4 text-amber-300" />
            <span>Phase 6: AI Weather-Aware Event Planner</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Weather & Event Planning
          </h1>
          <p className="mt-2 text-sky-100 text-sm sm:text-base max-w-2xl leading-relaxed">
            Real-time meteorological forecast & historical climate intelligence powered by Open-Meteo & Gemini AI.
            Identify atmospheric risks, optimize schedule timings, and save mitigation contingencies to your timeline.
          </p>
        </div>

        {weatherData && (
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-3.5 text-xs text-sky-100 space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-white">
              <Info className="w-3.5 h-3.5 text-sky-300" />
              <span>Data Source: {weatherData.data_source}</span>
            </div>
            <p className="text-[11px] text-sky-200">
              Retrieved: {weatherData.retrieved_at}
            </p>
          </div>
        )}
      </div>

      {/* 2. Location & Date Controls Toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <form onSubmit={handleManualSearch} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="flex-1 relative">
            <MapPin className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={cityInput}
              onChange={(e) => setCityInput(e.target.value)}
              placeholder="Celebration Location / City (e.g. Jaipur, Mumbai, Goa)"
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
              required
            />
          </div>

          <div className="w-full sm:w-56 relative">
            <Calendar className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="date"
              value={dateInput}
              onChange={(e) => setDateInput(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition font-medium"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition disabled:opacity-50 shrink-0"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Fetching Weather...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>Check Weather</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Notification Toast */}
      {timelineSaveNotice && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold flex items-center gap-2.5 shadow-sm animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{timelineSaveNotice}</span>
        </div>
      )}

      {/* Error Notice */}
      {fetchError && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-semibold flex items-center gap-2.5 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{fetchError}</span>
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col items-center justify-center h-64 space-y-3 bg-white rounded-2xl border border-slate-200">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-500">Querying Open-Meteo Meteorological System...</p>
        </div>
      )}

      {weatherData && !isLoading && (
        <>
          {/* 3. FORECAST ACCURACY & PREDICTION HORIZON BANNER */}
          <div
            className={`p-4 sm:p-5 rounded-2xl border flex items-start sm:items-center justify-between gap-4 shadow-xs ${
              weatherData.is_forecast
                ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
                : 'bg-amber-50/80 border-amber-200 text-amber-950'
            }`}
          >
            <div className="flex items-start gap-3.5">
              {weatherData.is_forecast ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-extrabold text-sm sm:text-base">
                    {weatherData.data_type_label}
                  </h3>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      weatherData.is_forecast
                        ? 'bg-emerald-200/80 text-emerald-900'
                        : 'bg-amber-200/80 text-amber-900'
                    }`}
                  >
                    {weatherData.is_forecast ? 'Active Horizon' : 'Multi-Year Climate Average'}
                  </span>
                </div>
                <p className="text-xs mt-1 text-slate-700 leading-relaxed">
                  {weatherData.is_forecast
                    ? `Live numerical weather prediction for ${weatherData.location} on ${weatherData.target_date}. Derived from active high-resolution meteorological models.`
                    : `Your event date (${weatherData.target_date}) is beyond the 16-day active forecasting horizon. Meteorological parameters are calculated from historical multi-year records for this calendar window.`}
                </p>
              </div>
            </div>

            <div className="hidden lg:block text-right shrink-0">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Target Date
              </span>
              <span className="text-sm font-extrabold text-slate-900">
                {weatherData.target_date}
              </span>
            </div>
          </div>

          {/* 4. CORE WEATHER METRICS CARDS (8 METRICS) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 sm:gap-4">
            {/* Condition */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Condition</span>
                {getWeatherIcon(weatherData.day_summary.weather_code, 'w-4 h-4')}
              </div>
              <p className="text-sm font-extrabold text-slate-900 mt-2 truncate">
                {weatherData.day_summary.condition_text}
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Sky & Atmosphere</span>
            </div>

            {/* Max Temp */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Max Temp</span>
                <Thermometer className="w-4 h-4 text-rose-500" />
              </div>
              <p className="text-lg font-extrabold text-slate-900 mt-2">
                {weatherData.day_summary.temp_max.toFixed(1)}°C
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Min: {weatherData.day_summary.temp_min.toFixed(1)}°C</span>
            </div>

            {/* Apparent Temp */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Feels Like</span>
                <Flame className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-lg font-extrabold text-amber-700 mt-2">
                {weatherData.day_summary.apparent_temp_max.toFixed(1)}°C
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Apparent Index</span>
            </div>

            {/* Rain Probability */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Rain Chance</span>
                <CloudRain className="w-4 h-4 text-indigo-500" />
              </div>
              <p className="text-lg font-extrabold text-indigo-700 mt-2">
                {weatherData.day_summary.rain_probability_max.toFixed(0)}%
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Precipitation prob</span>
            </div>

            {/* Precipitation */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Rain Volume</span>
                <Umbrella className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-lg font-extrabold text-blue-700 mt-2">
                {weatherData.day_summary.precipitation_sum.toFixed(1)} mm
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Total rainfall</span>
            </div>

            {/* Humidity */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Humidity</span>
                <Droplets className="w-4 h-4 text-indigo-500" />
              </div>
              <p className="text-lg font-extrabold text-indigo-700 mt-2">
                {weatherData.day_summary.humidity_mean.toFixed(0)}%
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Relative moisture</span>
            </div>

            {/* Wind Speed */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Wind Speed</span>
                <Wind className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-lg font-extrabold text-emerald-700 mt-2">
                {weatherData.day_summary.wind_speed_max.toFixed(1)} km/h
              </p>
              <span className="text-[10px] text-slate-500 mt-1">Maximum gusts</span>
            </div>

            {/* Sun Times */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[10px] font-bold uppercase tracking-wider">Sun Times</span>
                <Sunset className="w-4 h-4 text-amber-500" />
              </div>
              <div className="mt-2 space-y-0.5 text-xs font-bold text-slate-800">
                <div className="flex items-center gap-1">
                  <Sunrise className="w-3 h-3 text-amber-500" />
                  <span>{weatherData.day_summary.sunrise ? weatherData.day_summary.sunrise.slice(11, 16) : '06:30'}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Sunset className="w-3 h-3 text-rose-500" />
                  <span>{weatherData.day_summary.sunset ? weatherData.day_summary.sunset.slice(11, 16) : '18:15'}</span>
                </div>
              </div>
              <span className="text-[10px] text-slate-500">Golden hour approx</span>
            </div>
          </div>

          {/* 5. WEATHER RISK ANALYSIS SECTION */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h3 className="font-extrabold text-slate-900 text-lg">
                    Atmospheric Risk Assessment
                  </h3>
                  {getRiskBadge(weatherData.risk_assessment.overall_risk)}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {weatherData.risk_assessment.risk_summary}
                </p>
              </div>

              <span className="text-xs text-slate-400 font-medium">
                Configurable threshold safety bounds
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {weatherData.risk_assessment.factors.map((factor, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-slate-100 bg-slate-50/60 space-y-2 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-slate-700">{factor.category}</span>
                      {getRiskBadge(factor.risk_level)}
                    </div>
                    <p className="text-sm font-extrabold text-slate-900 mt-1.5">
                      {factor.value_display}
                    </p>
                    <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                      {factor.reason}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-400 block pt-2 border-t border-slate-200/60 font-mono">
                    {factor.threshold_note}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 6. RECHARTS WEATHER VISUALIZATIONS */}
          {chartData.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div>
                  <h4 className="font-bold text-slate-800 text-sm">
                    Meteorological Multi-Day Trend Visualizer
                  </h4>
                  <span className="text-xs text-slate-500">
                    Interactive atmospheric patterns across target calendar window
                  </span>
                </div>

                <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
                  <button
                    onClick={() => setChartView('temp')}
                    className={`px-3 py-1 rounded-lg transition ${
                      chartView === 'temp' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Temperature
                  </button>
                  <button
                    onClick={() => setChartView('rain')}
                    className={`px-3 py-1 rounded-lg transition ${
                      chartView === 'rain' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Rain & Probability
                  </button>
                  <button
                    onClick={() => setChartView('wind')}
                    className={`px-3 py-1 rounded-lg transition ${
                      chartView === 'wind' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Wind Speed
                  </button>
                </div>
              </div>

              <div className="h-64 sm:h-72 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  {chartView === 'temp' ? (
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0D9488" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#0D9488" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis unit="°C" domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="maxTemp" stroke="#0D9488" fill="url(#tempGradient)" name="Max Temp (°C)" />
                      <Area type="monotone" dataKey="apparentTemp" stroke="#F59E0B" fill="none" name="Feels Like (°C)" />
                      <Area type="monotone" dataKey="minTemp" stroke="#3B82F6" fill="none" name="Min Temp (°C)" />
                    </AreaChart>
                  ) : chartView === 'rain' ? (
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="left" unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" unit="mm" tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar yAxisId="left" dataKey="rainProb" fill="#6366F1" name="Rain Probability (%)" radius={[4, 4, 0, 0]} />
                      <Bar yAxisId="right" dataKey="precip" fill="#3B82F6" name="Precipitation (mm)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  ) : (
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis unit="km/h" tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="wind" fill="#10B981" name="Max Wind Speed (km/h)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 7. SMART EVENT RECOMMENDATIONS & TIMELINE SAVE */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <h3 className="font-extrabold text-slate-900 text-lg">
                  Smart Event Weather Recommendations
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Tailored contingencies for your {plan?.intake.event_type || 'celebration'}. Select action items to save directly to your timeline.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleSelectAllRecommendations}
                  className="px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold transition"
                >
                  {selectedRecommendations.length === weatherData.recommendations.length
                    ? 'Deselect All'
                    : 'Select All'}
                </button>

                <button
                  onClick={() => setIsConfirmModalOpen(true)}
                  disabled={selectedRecommendations.length === 0 || !plan}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition disabled:opacity-50"
                >
                  <ListPlus className="w-4 h-4" />
                  <span>Save to Timeline ({selectedRecommendations.length})</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {weatherData.recommendations.map((rec) => {
                const isSelected = selectedRecommendations.includes(rec.title);
                return (
                  <div
                    key={rec.id}
                    onClick={() => handleToggleRecommendation(rec.title)}
                    className={`p-4 rounded-xl border transition cursor-pointer flex flex-col justify-between space-y-3 ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-50/40 shadow-xs'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            rec.priority === 'Critical'
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : rec.priority === 'Recommended'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {rec.priority}
                        </span>

                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer"
                        />
                      </div>

                      <span className="text-[10px] uppercase font-bold text-slate-400 block mt-2">
                        {rec.category}
                      </span>
                      <h4 className="font-extrabold text-slate-900 text-sm mt-0.5">
                        {rec.title}
                      </h4>
                      <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                        {rec.description}
                      </p>
                    </div>

                    <div className="pt-2.5 border-t border-slate-100 space-y-1">
                      <p className="text-[11px] font-semibold text-indigo-900 bg-indigo-100/60 p-2 rounded-lg">
                        🎯 Action: {rec.action_item}
                      </p>
                      <span className="text-[10px] text-slate-400 block text-right font-medium">
                        Suggested Phase: {rec.suggested_timeline_phase}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 8. AI WEATHER ASSISTANT DRAWER / CHAT */}
          <div className="bg-gradient-to-br from-indigo-50/70 via-white to-sky-50/50 rounded-2xl border border-indigo-100 shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-indigo-600 rounded-xl text-white shadow-xs">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-slate-900 text-base">
                    AI Weather Assistant (Gemini Powered)
                  </h3>
                  <p className="text-xs text-slate-500">
                    Ask intelligent questions grounded in factual weather data for {weatherData.location}.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick Prompt Chips */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-xs font-semibold text-slate-600">Quick questions:</span>
              {[
                'Is this date suitable for an outdoor wedding?',
                'What precautions should I take for rain or heat?',
                'Should I arrange an indoor backup venue?',
                'What time would be suitable for an outdoor event?',
                'How can I protect decorations from wind and moisture?',
              ].map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleAskAi(chip)}
                  disabled={isAiLoading}
                  className="px-2.5 py-1 bg-white hover:bg-indigo-50 text-indigo-900 border border-indigo-200 rounded-lg text-[11px] font-medium transition shadow-2xs disabled:opacity-50"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Natural Language Query Bar */}
            <div className="flex flex-col sm:flex-row gap-2 pt-2">
              <input
                type="text"
                value={aiQuestion}
                onChange={(e) => setAiQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAskAi()}
                placeholder="Ask e.g. 'Can we do the ceremony at 4 PM without guests feeling too hot?'"
                className="flex-1 px-4 py-2.5 text-sm bg-white border border-indigo-200 rounded-xl focus:ring-2 focus:ring-indigo-500 transition"
              />
              <button
                onClick={() => handleAskAi()}
                disabled={isAiLoading || !aiQuestion.trim()}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-xs transition disabled:opacity-50 shrink-0"
              >
                {isAiLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Ask Weather AI</span>
                  </>
                )}
              </button>
            </div>

            {/* AI Answer Card */}
            {aiAnswer && (
              <div className="mt-4 p-5 rounded-xl bg-white border border-indigo-200 shadow-xs space-y-3 animate-in fade-in">
                <div className="flex items-center justify-between border-b border-indigo-50 pb-2.5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <span className="font-extrabold text-xs text-indigo-900">
                      Grounded Meteorological Advice
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      aiAnswer.is_forecast_based
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {aiAnswer.is_forecast_based ? 'Active Forecast Horizon' : 'Historical Reference Mode'}
                  </span>
                </div>

                <p className="text-xs text-slate-800 leading-relaxed font-normal whitespace-pre-line">
                  {aiAnswer.answer}
                </p>

                {aiAnswer.key_suggestions.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-700 block">
                      Recommended Action Items:
                    </span>
                    <ul className="space-y-1">
                      {aiAnswer.key_suggestions.map((s, idx) => (
                        <li key={idx} className="text-xs text-slate-600 flex items-start gap-1.5">
                          <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-2 text-[10px] text-slate-400 font-mono">
                  Grounding: {aiAnswer.data_grounding}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* 9. CONFIRMATION MODAL FOR SAVING TASKS TO TIMELINE */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <ListPlus className="w-5 h-5 text-indigo-600" />
                <h3 className="font-extrabold text-slate-900 text-base">
                  Confirm Timeline Integration
                </h3>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              You are about to save <strong>{selectedRecommendations.length}</strong> weather-mitigation task(s) directly into your event timeline. Duplicate tasks will be skipped automatically.
            </p>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2 max-h-48 overflow-y-auto">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Tasks to Add:
              </span>
              <ul className="space-y-1.5 text-xs text-slate-800">
                {selectedRecommendations.map((t, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 border border-slate-200 text-slate-700 hover:bg-slate-100 rounded-xl font-semibold text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveToTimeline}
                disabled={isSavingTasks}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {isSavingTasks ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Confirm & Save to Timeline</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WeatherPlannerTab;
