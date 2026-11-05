import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Mail,
  Send,
  Sparkles,
  Download,
  Copy,
  Check,
  Share2,
  Palette,
  Eye,
  RefreshCw,
  Bookmark,
  CheckCircle2,
  Trash2,
  Sliders,
  Globe,
  Calendar,
  MapPin,
  User,
  Users,
  FileText,
  Image as ImageIcon,
  MessageCircle,
  ExternalLink,
  ChevronRight,
  AlertCircle,
  Crown,
  PartyPopper,
  Briefcase,
  Heart,
  Flower2,
} from 'lucide-react';
import {
  FullEventPlan,
  GuestItem,
  InvitationLanguage,
  InvitationStyle,
  InvitationVariation,
  InvitationTextComponents,
  InvitationDesignConfig,
  InvitationTemplate,
  InvitationItem,
} from '../types';
import {
  generateInvitations,
  saveInvitation,
  getSavedInvitations,
  deleteSavedInvitation,
  exportDynamicInvitationPdf,
  getSavedInvitationPdfUrl,
  getGuests,
  markGuestInvitationSent,
} from '../api';

interface InvitationsTabProps {
  plan: FullEventPlan | null;
}

export const extractVenueFromPlan = (plan: FullEventPlan | null): string => {
  if (!plan) return '';
  // 1. Explicit intake venue
  if (plan.intake && (plan.intake as any).venue && (plan.intake as any).venue.trim()) {
    return (plan.intake as any).venue.trim();
  }
  // 2. Plan vendors
  if (plan.vendors && Array.isArray(plan.vendors)) {
    const venueVendor = plan.vendors.find(
      (v) =>
        v.category &&
        v.category.toLowerCase().includes('venue') &&
        v.vendor_name &&
        v.vendor_name.trim() &&
        !v.vendor_name.toLowerCase().includes('specialist') &&
        !v.vendor_name.toLowerCase().includes('provider')
    );
    if (venueVendor && venueVendor.vendor_name.trim()) {
      return venueVendor.vendor_name.trim();
    }
    const anyVenue = plan.vendors.find(
      (v) => v.category && v.category.toLowerCase().includes('venue') && v.vendor_name && v.vendor_name.trim()
    );
    if (anyVenue && anyVenue.vendor_name.trim()) {
      return anyVenue.vendor_name.trim();
    }
  }
  // 3. Fallback to city
  return plan.intake?.city ? `${plan.intake.city} Grand Hall` : 'Grand Celebration Venue';
};

export const formatTimeWithAmPm = (timeStr: string): string => {
  if (!timeStr) return '7:00 PM onwards';
  const t = timeStr.trim();
  const lower = t.toLowerCase();
  if (lower.includes('am') || lower.includes('pm')) {
    return t.includes('onwards') ? t : `${t} onwards`;
  }
  const match = t.match(/(\d{1,2}):(\d{2})/);
  if (match) {
    const hour = parseInt(match[1], 10);
    const minute = match[2];
    const period = hour >= 12 ? 'PM' : 'AM';
    const dispHour = hour % 12 === 0 ? 12 : hour % 12;
    return `${dispHour}:${minute} ${period} onwards`;
  }
  const numMatch = t.match(/(\d{1,2})/);
  if (numMatch) {
    const hour = parseInt(numMatch[1], 10);
    const period = hour >= 12 && hour < 24 ? 'PM' : (hour < 12 ? 'AM' : 'PM');
    const dispHour = hour % 12 === 0 ? 12 : hour % 12;
    return `${dispHour}:00 ${period} onwards`;
  }
  return `${t} onwards`;
};

export const extractStartTimeFromPlan = (plan: FullEventPlan | null): string => {
  if (!plan) return '7:00 PM onwards';
  const intakeTime = (plan.intake as any).start_time || (plan.intake as any).event_time;
  if (intakeTime && String(intakeTime).trim()) {
    return formatTimeWithAmPm(String(intakeTime).trim());
  }
  if (plan.timeline?.run_of_show?.length) {
    const mainSlot = plan.timeline.run_of_show.find(
      (r) =>
        !r.activity.toLowerCase().includes('pre-event setup') &&
        !r.activity.toLowerCase().includes('vendor arrival')
    );
    if (mainSlot && mainSlot.time_slot) {
      const slotStart = mainSlot.time_slot.split('-')[0].trim();
      return formatTimeWithAmPm(slotStart);
    }
    const firstSlot = plan.timeline.run_of_show[0].time_slot.split('-')[0].trim();
    return formatTimeWithAmPm(firstSlot);
  }
  const evType = (plan.intake?.event_type || '').toLowerCase();
  if (evType.includes('birthday')) return '3:00 PM onwards';
  if (evType.includes('community')) return '9:00 AM onwards';
  return '7:00 PM onwards';
};

// 7 Professional Built-in Templates
const TEMPLATE_PRESETS: Record<string, InvitationTemplate> = {
  traditional_indian_wedding: {
    id: 'traditional_indian_wedding',
    template_id: 'traditional_indian_wedding',
    name: 'Traditional Indian Wedding',
    category: 'Wedding',
    bg_theme: 'gold_vermilion',
    bg_color: '#FFFDF9',
    primary_color: '#991B1B',
    text_color: '#1F2937',
    accent_color: '#D97706',
    font_family: 'serif',
    font_size: 'medium',
    border_style: 'ornate_gold',
    layout: 'centered',
    decorative_element: 'mandala_diya',
  },
  royal_wedding: {
    id: 'royal_wedding',
    template_id: 'royal_wedding',
    name: 'Royal Wedding',
    category: 'Wedding',
    bg_theme: 'royal_navy',
    bg_color: '#0F172A',
    primary_color: '#F59E0B',
    text_color: '#F8FAFC',
    accent_color: '#FDE68A',
    font_family: 'display',
    font_size: 'medium',
    border_style: 'ornate_gold',
    layout: 'framed',
    decorative_element: 'royal_crest',
  },
  floral_birthday: {
    id: 'floral_birthday',
    template_id: 'floral_birthday',
    name: 'Floral Birthday',
    category: 'Birthday',
    bg_theme: 'floral_blush',
    bg_color: '#FFF5F5',
    primary_color: '#DB2777',
    text_color: '#374151',
    accent_color: '#F472B6',
    font_family: 'cursive',
    font_size: 'medium',
    border_style: 'floral',
    layout: 'centered',
    decorative_element: 'floral_wreath',
  },
  minimalist_birthday: {
    id: 'minimalist_birthday',
    template_id: 'minimalist_birthday',
    name: 'Minimalist Birthday',
    category: 'Birthday',
    bg_theme: 'minimalist_slate',
    bg_color: '#F8FAFC',
    primary_color: '#2563EB',
    text_color: '#0F172A',
    accent_color: '#64748B',
    font_family: 'sans',
    font_size: 'medium',
    border_style: 'minimal',
    layout: 'minimal',
    decorative_element: 'confetti_stars',
  },
  college_fest: {
    id: 'college_fest',
    template_id: 'college_fest',
    name: 'College Fest',
    category: 'Community',
    bg_theme: 'ultraviolet_teal',
    bg_color: '#111827',
    primary_color: '#8B5CF6',
    text_color: '#F9FAFB',
    accent_color: '#06B6D4',
    font_family: 'sans',
    font_size: 'medium',
    border_style: 'dashed',
    layout: 'split',
    decorative_element: 'geometric_badge',
  },
  corporate_event: {
    id: 'corporate_event',
    template_id: 'corporate_event',
    name: 'Corporate Event',
    category: 'Corporate',
    bg_theme: 'executive_platinum',
    bg_color: '#F1F5F9',
    primary_color: '#0F172A',
    text_color: '#334155',
    accent_color: '#3B82F6',
    font_family: 'serif',
    font_size: 'medium',
    border_style: 'double',
    layout: 'framed',
    decorative_element: 'none',
  },
  anniversary: {
    id: 'anniversary',
    template_id: 'anniversary',
    name: 'Anniversary Celebration',
    category: 'Anniversary',
    bg_theme: 'champagne_burgundy',
    bg_color: '#FFFBEB',
    primary_color: '#831843',
    text_color: '#292524',
    accent_color: '#D97706',
    font_family: 'cursive',
    font_size: 'medium',
    border_style: 'ornate_gold',
    layout: 'centered',
    decorative_element: 'royal_crest',
  },
};

export const InvitationsTab: React.FC<InvitationsTabProps> = ({ plan }) => {
  // Event & Guest State
  const [guests, setGuests] = useState<GuestItem[]>([]);
  const [selectedGuestId, setSelectedGuestId] = useState<string>('all');
  const [selectedGuest, setSelectedGuest] = useState<GuestItem | null>(null);

  // Form Inputs
  const [eventName, setEventName] = useState<string>('');
  const [eventType, setEventType] = useState<string>('Wedding');
  const [hostNames, setHostNames] = useState<string>('');
  const [eventDate, setEventDate] = useState<string>('');
  const [eventTime, setEventTime] = useState<string>('7:00 PM onwards');
  const [venue, setVenue] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [additionalNotes, setAdditionalNotes] = useState<string>('');
  const [language, setLanguage] = useState<InvitationLanguage>('English');
  const [style, setStyle] = useState<InvitationStyle>('Traditional');
  const [tone, setTone] = useState<string>('Warm & Welcoming');

  // Generation Results (3 Variations)
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [variations, setVariations] = useState<InvitationVariation[]>([]);
  const [activeVariationIdx, setActiveVariationIdx] = useState<number>(0);
  const [generationModel, setGenerationModel] = useState<string>('');
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Editable Text Components for Active Variation
  const [activeComponents, setActiveComponents] = useState<InvitationTextComponents>({
    personalized_greeting: '',
    event_details: '',
    invitation_message: '',
    closing_message: '',
    full_text: '',
  });

  // Card Design Customization
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>('traditional_indian_wedding');
  const [designConfig, setDesignConfig] = useState<InvitationDesignConfig>(
    TEMPLATE_PRESETS.traditional_indian_wedding
  );

  // Saved Invitations
  const [savedInvitations, setSavedInvitations] = useState<InvitationItem[]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccessNotice, setSaveSuccessNotice] = useState<string | null>(null);

  // Sharing & Status Feedback
  const [copiedTextNotice, setCopiedTextNotice] = useState<boolean>(false);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [isExportingPng, setIsExportingPng] = useState<boolean>(false);
  const [markingSentNotice, setMarkingSentNotice] = useState<string | null>(null);

  const cardPreviewRef = useRef<HTMLDivElement>(null);

  // Auto-fill from Plan & Load Guests & Saved Invitations
  useEffect(() => {
    if (plan) {
      const title = plan.intake.title || '';
      const evDate = plan.intake.date || '';
      const evCity = plan.intake.city || '';
      const realVenue = extractVenueFromPlan(plan);
      const realTime = extractStartTimeFromPlan(plan);
      const realHosts = plan.intake.host_names || 'The Host Family';

      setEventName(title);
      setEventType(
        plan.intake.event_type
          ? plan.intake.event_type.charAt(0).toUpperCase() + plan.intake.event_type.slice(1)
          : 'Wedding'
      );
      setEventDate(evDate);
      setLocation(evCity);
      setVenue(realVenue);
      setEventTime(realTime);
      setHostNames(realHosts);

      // Auto-populate activeComponents with dynamic event defaults so Live Preview & PDF are never empty
      const initialDetails = `Date: ${evDate} | Time: ${realTime}\nVenue: ${realVenue}, ${evCity}`;
      const initialMsg = `Together with our families, ${realHosts} cordially invite you to join us in celebrating '${title}'. Your gracious presence and warm blessings will make this celebration truly special.`;
      const initialClosing = `With warm regards,\n${realHosts}`;
      setActiveComponents({
        personalized_greeting: 'Dear Esteemed Guests & Family,',
        event_details: initialDetails,
        invitation_message: initialMsg,
        closing_message: initialClosing,
        full_text: `Dear Esteemed Guests & Family,\n\n${initialMsg}\n\n${initialDetails}\n\n${initialClosing}`,
      });

      // Pick default template matching event type
      const lowerType = (plan.intake.event_type || '').toLowerCase();
      if (lowerType.includes('wedding')) {
        applyTemplate('traditional_indian_wedding');
        setStyle('Traditional');
      } else if (lowerType.includes('birthday')) {
        applyTemplate('floral_birthday');
        setStyle('Fun and Casual');
      } else {
        applyTemplate('corporate_event');
        setStyle('Modern');
      }

      loadGuests(plan.event_id);
      loadSavedInvitations(plan.event_id);
    }
  }, [plan?.event_id]);

  const loadGuests = async (eventId: string) => {
    try {
      const data = await getGuests(eventId);
      setGuests(data);
    } catch (e) {
      console.error('Failed to load guests for invitation personalization:', e);
    }
  };

  const loadSavedInvitations = async (eventId: string) => {
    try {
      const data = await getSavedInvitations(eventId);
      setSavedInvitations(data);
    } catch (e) {
      console.error('Failed to load saved invitations:', e);
    }
  };

  // Sync selected guest
  const handleGuestSelect = (guestId: string) => {
    setSelectedGuestId(guestId);
    if (guestId === 'all') {
      setSelectedGuest(null);
    } else {
      const found = guests.find((g) => g.id === guestId) || null;
      setSelectedGuest(found);
    }
  };

  // Switch Template
  const applyTemplate = (templateKey: string) => {
    setSelectedTemplateKey(templateKey);
    const tmpl = TEMPLATE_PRESETS[templateKey];
    if (tmpl) {
      setDesignConfig({
        template_id: tmpl.id,
        bg_theme: tmpl.bg_theme,
        bg_color: tmpl.bg_color,
        primary_color: tmpl.primary_color,
        text_color: tmpl.text_color,
        accent_color: tmpl.accent_color,
        font_family: tmpl.font_family,
        font_size: tmpl.font_size,
        border_style: tmpl.border_style,
        layout: tmpl.layout,
        decorative_element: tmpl.decorative_element,
      });
    }
  };

  // Generate 3 Variations via Backend API
  const handleGenerate = async () => {
    if (!eventName.trim()) {
      setGenerationError('Please enter an event name/title.');
      return;
    }
    setIsGenerating(true);
    setGenerationError(null);
    try {
      const res = await generateInvitations({
        event_id: plan?.event_id,
        guest_id: selectedGuest ? selectedGuest.id : undefined,
        event_name: eventName,
        event_type: eventType,
        host_names: hostNames || 'The Host Family',
        event_date: eventDate || 'Date to be announced',
        event_time: eventTime || '7:00 PM',
        venue: venue || 'Celebration Hall',
        location: location || 'City',
        additional_instructions: additionalNotes || undefined,
        language,
        style,
        tone,
      });

      setVariations(res.variations);
      setGenerationModel(res.model_used);
      if (res.variations.length > 0) {
        setActiveVariationIdx(0);
        setActiveComponents(res.variations[0].components);
      }
    } catch (err: any) {
      setGenerationError(err.message || 'Failed to generate invitations.');
    } finally {
      setIsGenerating(false);
    }
  };

  // When user switches variation tab
  const selectVariation = (idx: number) => {
    setActiveVariationIdx(idx);
    if (variations[idx]) {
      setActiveComponents({ ...variations[idx].components });
    }
  };

  // Handle manual edits to active variation text components
  const handleComponentChange = (field: keyof InvitationTextComponents, value: string) => {
    const updated = { ...activeComponents, [field]: value };
    // Recompute full text
    updated.full_text = `${updated.personalized_greeting}\n\n${updated.invitation_message}\n\n${updated.event_details}\n\n${updated.closing_message}`;
    setActiveComponents(updated);

    // Also update in variations list for current index
    if (variations[activeVariationIdx]) {
      const updatedVars = [...variations];
      updatedVars[activeVariationIdx] = {
        ...updatedVars[activeVariationIdx],
        components: updated,
      };
      setVariations(updatedVars);
    }
  };

  // Copy invitation text to clipboard
  const handleCopyText = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(activeComponents.full_text);
        setCopiedTextNotice(true);
        setTimeout(() => setCopiedTextNotice(false), 2500);
      } else {
        throw new Error('Clipboard API unavailable');
      }
    } catch {
      // Fallback for headless browsers or restricted clipboard environments
      try {
        const textarea = document.createElement('textarea');
        textarea.value = activeComponents.full_text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        setCopiedTextNotice(true);
        setTimeout(() => setCopiedTextNotice(false), 2500);
      } catch {
        // Non-blocking fallback
      }
    }
  };

  // Share on WhatsApp
  const handleWhatsAppShare = () => {
    const textToShare = activeComponents.full_text || `${eventName} - You're Invited!`;
    const encoded = encodeURIComponent(textToShare);
    window.open(`https://api.whatsapp.com/send?text=${encoded}`, '_blank');
  };

  // Client-Side Canvas Render for High-Res PNG Download
  const handleDownloadPng = async () => {
    setIsExportingPng(true);
    try {
      // Ensure web fonts are completely ready before measuring and drawing
      if (typeof document !== 'undefined' && document.fonts && document.fonts.ready) {
        await document.fonts.ready;
      }

      const canvas = document.createElement('canvas');
      const width = 800;
      const height = 1120;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Could not initialize canvas context');

      // 1. Background Fill
      ctx.fillStyle = designConfig.bg_color || '#FFFDF9';
      ctx.fillRect(0, 0, width, height);

      // Rounded rect utility helper with backward-compatibility fallback
      const drawRoundRect = (
        c: CanvasRenderingContext2D,
        rx: number,
        ry: number,
        rw: number,
        rh: number,
        radius: number
      ) => {
        if (typeof c.roundRect === 'function') {
          c.beginPath();
          c.roundRect(rx, ry, rw, rh, radius);
        } else {
          c.beginPath();
          c.moveTo(rx + radius, ry);
          c.lineTo(rx + rw - radius, ry);
          c.quadraticCurveTo(rx + rw, ry, rx + rw, ry + radius);
          c.lineTo(rx + rw, ry + rh - radius);
          c.quadraticCurveTo(rx + rw, ry + rh, rx + rw - radius, ry + rh);
          c.lineTo(rx + radius, ry + rh);
          c.quadraticCurveTo(rx, ry + rh, rx, ry + rh - radius);
          c.lineTo(rx, ry + radius);
          c.quadraticCurveTo(rx, ry, rx + radius, ry);
          c.closePath();
        }
      };

      // 2. Borders & Corner Accents
      const borderStyle = designConfig.border_style || 'ornate_gold';
      const primaryColor = designConfig.primary_color || '#991B1B';
      const accentColor = designConfig.accent_color || '#D97706';
      const textColor = designConfig.text_color || '#1F2937';

      // Outer Border
      ctx.save();
      ctx.lineWidth = borderStyle === 'minimal' ? 1.5 : 2.5;
      ctx.strokeStyle = borderStyle === 'double' ? primaryColor : accentColor;
      ctx.strokeRect(30, 30, width - 60, height - 60);

      // Inner Border
      if (borderStyle === 'dashed') {
        ctx.setLineDash([8, 6]);
      }
      ctx.lineWidth = borderStyle === 'double' ? 1.5 : 1.2;
      ctx.strokeStyle = borderStyle === 'double' ? accentColor : primaryColor;
      ctx.strokeRect(40, 40, width - 80, height - 80);
      ctx.restore();

      // Corner Accents
      const corners = [
        [40, 40, 1, 1],
        [width - 40, 40, -1, 1],
        [40, height - 40, 1, -1],
        [width - 40, height - 40, -1, -1],
      ];
      ctx.fillStyle = accentColor;
      ctx.strokeStyle = accentColor;
      ctx.lineWidth = 1.2;
      corners.forEach(([cx, cy, dirX, dirY]) => {
        // Corner Dot
        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.fill();

        // Elegant corner brackets for ornate/royal/floral
        if (borderStyle === 'ornate_gold' || borderStyle === 'double' || borderStyle === 'floral') {
          ctx.beginPath();
          ctx.moveTo(cx + dirX * 14, cy);
          ctx.lineTo(cx + dirX * 14, cy + dirY * 14);
          ctx.lineTo(cx, cy + dirY * 14);
          ctx.stroke();

          // Small diamond accent inside bracket
          ctx.beginPath();
          const dX = cx + dirX * 8;
          const dY = cy + dirY * 8;
          ctx.moveTo(dX, dY - 2.5);
          ctx.lineTo(dX + 2.5, dY);
          ctx.lineTo(dX, dY + 2.5);
          ctx.lineTo(dX - 2.5, dY);
          ctx.closePath();
          ctx.fill();
        }
      });

      // 3. Typography & Font Resolution with Indic Support
      const lang = language || 'English';
      const configFont = designConfig.font_family || 'serif';

      const getTitleFontFamily = () => {
        if (lang === 'Gujarati') {
          return '"Noto Sans Gujarati", "Shruti", "Gujarati Sangam MN", "Nirmala UI", sans-serif';
        }
        if (lang === 'Hindi') {
          return '"Noto Sans Devanagari", "Mangal", "Devanagari Sangam MN", "Nirmala UI", sans-serif';
        }
        if (configFont === 'sans') {
          return '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        }
        if (configFont === 'cursive') {
          return '"Playfair Display", "Great Vibes", "Georgia", serif';
        }
        return '"Cinzel", "Playfair Display", "Times New Roman", Georgia, serif';
      };

      const getBodyFontFamily = () => {
        if (lang === 'Gujarati') {
          return '"Noto Sans Gujarati", "Shruti", "Gujarati Sangam MN", "Nirmala UI", sans-serif';
        }
        if (lang === 'Hindi') {
          return '"Noto Sans Devanagari", "Mangal", "Devanagari Sangam MN", "Nirmala UI", sans-serif';
        }
        if (configFont === 'sans') {
          return '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        }
        return '"Georgia", "Times New Roman", serif';
      };

      // 4. Line Wrapping & Measurement Helper (Pass 1)
      interface MeasuredBlock {
        type: 'text';
        lines: string[];
        lineHeight: number;
        font: string;
        color: string;
        totalHeight: number;
        isItalic?: boolean;
      }

      const measureTextBlock = (
        text: string,
        maxWidth: number,
        fontSize: number,
        lineHeight: number,
        fontFamily: string,
        fontWeight: string,
        color: string,
        isItalic = false
      ): MeasuredBlock => {
        const fontStr = `${isItalic ? 'italic ' : ''}${fontWeight} ${fontSize}px ${fontFamily}`;
        ctx.font = fontStr;
        const resultLines: string[] = [];
        const paragraphs = text.split('\n');

        for (let p = 0; p < paragraphs.length; p++) {
          const para = paragraphs[p];
          if (!para.trim()) {
            if (p > 0 && p < paragraphs.length - 1) {
              resultLines.push('');
            }
            continue;
          }
          const words = para.split(' ');
          let currentLine = '';
          for (let n = 0; n < words.length; n++) {
            const testLine = currentLine ? `${currentLine} ${words[n]}` : words[n];
            const metrics = ctx.measureText(testLine);
            if (metrics.width > maxWidth && currentLine) {
              resultLines.push(currentLine.trim());
              currentLine = words[n];
            } else {
              currentLine = testLine;
            }
          }
          if (currentLine) {
            resultLines.push(currentLine.trim());
          }
        }

        let totalH = 0;
        for (const l of resultLines) {
          totalH += l === '' ? lineHeight * 0.5 : lineHeight;
        }

        return {
          type: 'text',
          lines: resultLines,
          lineHeight,
          font: fontStr,
          color,
          totalHeight: Math.max(totalH, lineHeight),
          isItalic,
        };
      };

      // Check for user religious mantra to avoid duplication in PNG export
      const GANESH_KEYWORDS = ['ગણેશાય નમઃ', 'શ્રી ગણેશ', 'શ્રીગણેશ', 'ગણેશજી', 'गणेशाय नमः', 'श्री गणेश', 'श्रीगणेश', 'ganeshaya namaha'];
      const userTextHasMantra = GANESH_KEYWORDS.some(k => 
        (activeComponents.personalized_greeting || '').toLowerCase().includes(k) || 
        (activeComponents.invitation_message || '').toLowerCase().includes(k)
      );

      // Determine Decorative Top Motif Text
      let motif = '• • •';
      if (designConfig.decorative_element === 'mandala_diya') {
        if (userTextHasMantra) {
          motif = language === 'Hindi' ? '— ॐ —' : language === 'Gujarati' ? '— ૐ —' : '— • —';
        } else {
          motif = language === 'Hindi' ? '॥ ॐ श्री गणेशाय नमः ॥' : language === 'Gujarati' ? '॥ ૐ શ્રી ગણેશાય નમઃ ॥' : '• CORDIAL INVITATION •';
        }
      } else if (designConfig.decorative_element === 'royal_crest') {
        motif = language === 'Hindi' ? '— शाही निमंत्रण —' : language === 'Gujarati' ? '— રાજવી નિમંત્રણ —' : '— ROYAL INVITATION —';
      } else if (designConfig.decorative_element === 'floral_wreath') {
        motif = language === 'Hindi' ? '— मंगल महोत्सव —' : language === 'Gujarati' ? '— મંગલ મહોત્સવ —' : '— CELEBRATION —';
      } else if (designConfig.decorative_element === 'confetti_stars') {
        motif = language === 'Hindi' ? '— आनंदोत्सव —' : language === 'Gujarati' ? '— આનંદમય ઉજવણી —' : "— LET'S CELEBRATE —";
      } else if (designConfig.decorative_element === 'geometric_badge') {
        motif = '— • —';
      }

      // Check text lengths to select standard vs compact sizing
      const totalCharCount =
        (eventName || '').length +
        (activeComponents.personalized_greeting || '').length +
        (activeComponents.invitation_message || '').length +
        (activeComponents.event_details || '').length +
        (activeComponents.closing_message || '').length;

      const isCompact = totalCharCount > 650;

      // Font parameters
      const titleSize = isCompact ? 28 : (eventName.length > 40 ? 30 : 34);
      const titleLineH = isCompact ? 36 : 42;
      const greetingSize = isCompact ? 18 : 21;
      const greetingLineH = isCompact ? 26 : 30;
      const messageSize = isCompact ? 16 : 18;
      const messageLineH = isCompact ? 26 : 30;
      const closingSize = isCompact ? 17 : 19;
      const closingLineH = isCompact ? 26 : 29;

      const contentMaxWidth = width - 180; // 620px

      // Measure Sections
      // 1. Top Motif & Decorative Divider
      const topMotifHeight = 44;

      // 2. Title Block
      const titleBlock = measureTextBlock(
        eventName || 'Celebration',
        contentMaxWidth,
        titleSize,
        titleLineH,
        getTitleFontFamily(),
        'bold',
        primaryColor
      );

      // 3. Greeting Block
      let greetingBlock: MeasuredBlock | null = null;
      if (activeComponents.personalized_greeting?.trim()) {
        greetingBlock = measureTextBlock(
          activeComponents.personalized_greeting.trim(),
          contentMaxWidth,
          greetingSize,
          greetingLineH,
          getBodyFontFamily(),
          lang === 'English' ? '500' : 'bold',
          primaryColor,
          lang === 'English'
        );
      }

      // 4. Main Invitation Message Block
      let messageBlock: MeasuredBlock | null = null;
      if (activeComponents.invitation_message?.trim()) {
        messageBlock = measureTextBlock(
          activeComponents.invitation_message.trim(),
          contentMaxWidth - 20,
          messageSize,
          messageLineH,
          getBodyFontFamily(),
          'normal',
          textColor
        );
      }

      // 5. Event Details Card Block
      interface DetailsCardBlock {
        type: 'details';
        boxWidth: number;
        boxHeight: number;
        headerTitle: string;
        lines: string[];
        lineHeight: number;
        paddingX: number;
        paddingY: number;
      }

      let detailsBlock: DetailsCardBlock | null = null;
      if (activeComponents.event_details?.trim()) {
        const detailsHeader =
          lang === 'Hindi'
            ? '✦ कार्यक्रम विवरण ✦'
            : lang === 'Gujarati'
            ? '✦ કાર્યક્રમ વિગત ✦'
            : '✦ EVENT DETAILS ✦';

        const rawDetailsLines = activeComponents.event_details.split('\n');
        const boxWidth = Math.min(contentMaxWidth, 580);
        const paddingX = 26;
        const paddingY = isCompact ? 16 : 22;
        const maxTextW = boxWidth - paddingX * 2;
        const detLineH = isCompact ? 24 : 27;

        // Wrap each detail line if necessary
        ctx.font = `15px ${getBodyFontFamily()}`;
        const wrappedDetailLines: string[] = [];
        for (const rawLine of rawDetailsLines) {
          if (!rawLine.trim()) continue;
          const words = rawLine.split(' ');
          let cur = '';
          for (let w = 0; w < words.length; w++) {
            const test = cur ? `${cur} ${words[w]}` : words[w];
            if (ctx.measureText(test).width > maxTextW && cur) {
              wrappedDetailLines.push(cur.trim());
              cur = words[w];
            } else {
              cur = test;
            }
          }
          if (cur) wrappedDetailLines.push(cur.trim());
        }

        const boxHeight =
          paddingY * 2 + 22 + (isCompact ? 12 : 16) + wrappedDetailLines.length * detLineH;

        detailsBlock = {
          type: 'details',
          boxWidth,
          boxHeight,
          headerTitle: detailsHeader,
          lines: wrappedDetailLines,
          lineHeight: detLineH,
          paddingX,
          paddingY,
        };
      }

      // 6. Closing Message Block
      let closingBlock: MeasuredBlock | null = null;
      if (activeComponents.closing_message?.trim()) {
        closingBlock = measureTextBlock(
          activeComponents.closing_message.trim(),
          contentMaxWidth,
          closingSize,
          closingLineH,
          getBodyFontFamily(),
          lang === 'English' ? '600' : 'bold',
          primaryColor,
          lang === 'English'
        );
      }

      // 7. Bottom Anchor Flourish
      const bottomOrnamentHeight = 26;

      // Group into active flow elements
      type FlowElement =
        | { type: 'motif'; height: number }
        | { type: 'title'; block: MeasuredBlock; height: number }
        | { type: 'greeting'; block: MeasuredBlock; height: number }
        | { type: 'message'; block: MeasuredBlock; height: number }
        | { type: 'details'; block: DetailsCardBlock; height: number }
        | { type: 'closing'; block: MeasuredBlock; height: number }
        | { type: 'ornament'; height: number };

      const flowElements: FlowElement[] = [{ type: 'motif', height: topMotifHeight }];
      flowElements.push({ type: 'title', block: titleBlock, height: titleBlock.totalHeight });
      if (greetingBlock) {
        flowElements.push({ type: 'greeting', block: greetingBlock, height: greetingBlock.totalHeight });
      }
      if (messageBlock) {
        flowElements.push({ type: 'message', block: messageBlock, height: messageBlock.totalHeight });
      }
      if (detailsBlock) {
        flowElements.push({ type: 'details', block: detailsBlock, height: detailsBlock.boxHeight });
      }
      if (closingBlock) {
        flowElements.push({ type: 'closing', block: closingBlock, height: closingBlock.totalHeight });
      }
      flowElements.push({ type: 'ornament', height: bottomOrnamentHeight });

      // Pass 2: Vertical Distribution Calculation
      const topSafeY = 65;
      const bottomSafeY = 1055;
      const availableHeight = bottomSafeY - topSafeY; // 990px

      const totalContentHeight = flowElements.reduce((sum, el) => sum + el.height, 0);
      const numGaps = flowElements.length - 1;
      const totalSlack = availableHeight - totalContentHeight;

      // Target gap distribution across elements and top/bottom padding
      const targetGap = totalSlack / (numGaps + 2);
      const gap = Math.min(Math.max(targetGap, 16), 44);

      // Remaining slack distributed symmetrically to top & bottom buffers
      const leftoverSlack = totalSlack - (numGaps * gap);
      const topBuffer = Math.max(26, leftoverSlack / 2);
      let currentY = topSafeY + topBuffer;

      // Pass 3: Render Elements
      for (const el of flowElements) {
        if (el.type === 'motif') {
          // Top Motif text
          ctx.font = `bold 16px ${getBodyFontFamily()}`;
          ctx.fillStyle = accentColor;
          ctx.textAlign = 'center';
          ctx.fillText(motif, width / 2, currentY + 16);

          // Subtle ornamental divider under motif
          const divY = currentY + 34;
          ctx.beginPath();
          ctx.strokeStyle = accentColor;
          ctx.lineWidth = 1;
          ctx.moveTo(width / 2 - 70, divY);
          ctx.lineTo(width / 2 - 12, divY);
          ctx.moveTo(width / 2 + 12, divY);
          ctx.lineTo(width / 2 + 70, divY);
          ctx.stroke();

          // Center diamond glyph
          ctx.beginPath();
          ctx.fillStyle = accentColor;
          ctx.moveTo(width / 2, divY - 3.5);
          ctx.lineTo(width / 2 + 3.5, divY);
          ctx.lineTo(width / 2, divY + 3.5);
          ctx.lineTo(width / 2 - 3.5, divY);
          ctx.closePath();
          ctx.fill();

          currentY += el.height + gap;
        } else if (el.type === 'title') {
          ctx.font = el.block.font;
          ctx.fillStyle = el.block.color;
          ctx.textAlign = 'center';
          let lineY = currentY + el.block.lineHeight * 0.85;
          for (const line of el.block.lines) {
            ctx.fillText(line, width / 2, lineY);
            lineY += el.block.lineHeight;
          }
          currentY += el.height + gap;
        } else if (el.type === 'greeting') {
          ctx.font = el.block.font;
          ctx.fillStyle = el.block.color;
          ctx.textAlign = 'center';
          let lineY = currentY + el.block.lineHeight * 0.85;
          for (const line of el.block.lines) {
            ctx.fillText(line, width / 2, lineY);
            lineY += el.block.lineHeight;
          }
          currentY += el.height + gap;
        } else if (el.type === 'message') {
          ctx.font = el.block.font;
          ctx.fillStyle = el.block.color;
          ctx.textAlign = 'center';
          let lineY = currentY + el.block.lineHeight * 0.85;
          for (const line of el.block.lines) {
            if (line === '') {
              lineY += el.block.lineHeight * 0.5;
            } else {
              ctx.fillText(line, width / 2, lineY);
              lineY += el.block.lineHeight;
            }
          }
          currentY += el.height + gap;
        } else if (el.type === 'details') {
          const d = el.block;
          const boxX = (width - d.boxWidth) / 2;
          const boxY = currentY;

          // Box Card Background & Border
          const isDarkBg = designConfig.bg_color === '#0F172A' || designConfig.bg_color === '#111827';
          ctx.fillStyle = isDarkBg ? '#1E293B' : '#FFFFFF';
          drawRoundRect(ctx, boxX, boxY, d.boxWidth, d.boxHeight, 14);
          ctx.fill();

          ctx.lineWidth = 1.5;
          ctx.strokeStyle = accentColor;
          ctx.stroke();

          // Details Header Title
          ctx.font = `bold 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
          ctx.fillStyle = primaryColor;
          ctx.textAlign = 'center';
          ctx.fillText(d.headerTitle, width / 2, boxY + d.paddingY + 12);

          // Header underline flourish
          const lineY = boxY + d.paddingY + 22;
          ctx.beginPath();
          ctx.strokeStyle = `${accentColor}80`;
          ctx.lineWidth = 1;
          ctx.moveTo(width / 2 - 60, lineY);
          ctx.lineTo(width / 2 + 60, lineY);
          ctx.stroke();

          // Detail Lines
          ctx.font = `15px ${getBodyFontFamily()}`;
          ctx.fillStyle = textColor;
          let detY = lineY + (isCompact ? 18 : 22);
          for (const dLine of d.lines) {
            ctx.fillText(dLine, width / 2, detY);
            detY += d.lineHeight;
          }

          currentY += el.height + gap;
        } else if (el.type === 'closing') {
          ctx.font = el.block.font;
          ctx.fillStyle = el.block.color;
          ctx.textAlign = 'center';
          let lineY = currentY + el.block.lineHeight * 0.85;
          for (const line of el.block.lines) {
            ctx.fillText(line, width / 2, lineY);
            lineY += el.block.lineHeight;
          }
          currentY += el.height + gap;
        } else if (el.type === 'ornament') {
          // Bottom Anchor Ornament
          const ornY = currentY + 12;
          ctx.fillStyle = accentColor;
          ctx.strokeStyle = accentColor;
          ctx.textAlign = 'center';
          ctx.font = '14px serif';
          ctx.fillText('— ❖ —', width / 2, ornY);

          // Subtle side accent lines
          ctx.beginPath();
          ctx.lineWidth = 0.8;
          ctx.moveTo(width / 2 - 80, ornY - 4);
          ctx.lineTo(width / 2 - 28, ornY - 4);
          ctx.moveTo(width / 2 + 28, ornY - 4);
          ctx.lineTo(width / 2 + 80, ornY - 4);
          ctx.stroke();

          currentY += el.height;
        }
      }

      // Convert to blob and download
      canvas.toBlob((blob) => {
        if (!blob) throw new Error('Canvas export failed');
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanName = eventName.replace(/[^a-zA-Z0-9]/g, '_') || 'Event';
        a.download = `${cleanName}_Invitation.png`;
        a.click();
        URL.revokeObjectURL(url);
      }, 'image/png');
    } catch (e: any) {
      alert(`PNG export failed: ${e.message}`);
    } finally {
      setIsExportingPng(false);
    }
  };

  // Download PDF via Backend ReportLab Endpoint
  const handleDownloadPdf = async () => {
    setIsExportingPdf(true);
    try {
      const blob = await exportDynamicInvitationPdf(
        eventName || 'Celebration Invitation',
        language,
        activeComponents,
        designConfig,
        {
          event_name: eventName,
          event_type: eventType,
          event_date: eventDate,
          event_time: eventTime,
          venue: venue,
          location: location,
          host_names: hostNames,
          additional_notes: additionalNotes,
        }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cleanName = eventName.replace(/[^a-zA-Z0-9]/g, '_') || 'Event';
      a.download = `${cleanName}_Card.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`PDF export failed: ${e.message}`);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Save Invitation to Database
  const handleSaveInvitation = async () => {
    if (!plan) return;
    setIsSaving(true);
    try {
      const saved = await saveInvitation(plan.event_id, {
        event_id: plan.event_id,
        guest_id: selectedGuest ? selectedGuest.id : undefined,
        title: `${eventName} (${language} - ${style})`,
        language,
        style,
        template_id: designConfig.template_id,
        text_components: activeComponents,
        design_config: designConfig,
      });

      setSavedInvitations([saved, ...savedInvitations.filter((i) => i.id !== saved.id)]);
      setSaveSuccessNotice('Invitation saved successfully!');
      setTimeout(() => setSaveSuccessNotice(null), 3000);
    } catch (e: any) {
      alert(`Failed to save invitation: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Load a Saved Invitation Back into Active Editor
  const handleLoadSaved = (inv: InvitationItem) => {
    setLanguage(inv.language as InvitationLanguage);
    setStyle(inv.style as InvitationStyle);
    setDesignConfig(inv.design_config);
    setSelectedTemplateKey(inv.design_config.template_id || 'traditional_indian_wedding');
    setActiveComponents(inv.text_components);
    // Put into variations as current
    setVariations([
      {
        variation_id: 1,
        variation_name: inv.title,
        components: inv.text_components,
      },
    ]);
    setActiveVariationIdx(0);
    if (inv.guest_id) {
      handleGuestSelect(inv.guest_id);
    }
    // Scroll up smoothly to editor
    window.scrollTo({ top: 300, behavior: 'smooth' });
  };

  // Delete a Saved Invitation
  const handleDeleteSaved = async (invId: string) => {
    if (!confirm('Are you sure you want to delete this saved invitation?')) return;
    try {
      await deleteSavedInvitation(invId);
      setSavedInvitations(savedInvitations.filter((i) => i.id !== invId));
    } catch (e: any) {
      alert(`Failed to delete invitation: ${e.message}`);
    }
  };

  // Explicitly Mark Invitation as Sent to Selected Guest
  const handleConfirmMarkSent = async () => {
    if (!plan || !selectedGuest) return;
    try {
      const updated = await markGuestInvitationSent(plan.event_id, selectedGuest.id);
      setSelectedGuest(updated);
      setGuests(guests.map((g) => (g.id === updated.id ? updated : g)));
      setMarkingSentNotice(`Marked as 'Sent' to ${updated.full_name} in Guest Management! RSVP remains '${updated.rsvp_status}'.`);
      setTimeout(() => setMarkingSentNotice(null), 4000);
    } catch (e: any) {
      alert(`Failed to mark as sent: ${e.message}`);
    }
  };

  // Decorative SVG Motif Component for Card Preview
  const renderCardMotif = () => {
    const elem = designConfig.decorative_element;
    const accent = designConfig.accent_color;

    const GANESH_KEYWORDS = ['ગણેશાય નમઃ', 'શ્રી ગણેશ', 'શ્રીગણેશ', 'ગણેશજી', 'गणेशाय नमः', 'श्री गणेश', 'श्रीगणेश', 'ganeshaya namaha'];
    const userTextHasMantra = GANESH_KEYWORDS.some(k => 
      (activeComponents.personalized_greeting || '').toLowerCase().includes(k) || 
      (activeComponents.invitation_message || '').toLowerCase().includes(k)
    );

    if (elem === 'mandala_diya') {
      const motifLabel = userTextHasMantra
        ? (language === 'Hindi' ? '— ॐ —' : language === 'Gujarati' ? '— ૐ —' : '— • —')
        : (language === 'Hindi' ? '॥ ॐ श्री गणेशाय नमः ॥' : language === 'Gujarati' ? '॥ ૐ શ્રી ગણેશાય નમઃ ॥' : '✦ CORDIAL INVITATION ✦');

      return (
        <div className="flex flex-col items-center justify-center my-2 space-y-1">
          <svg className="w-10 h-10" viewBox="0 0 100 100" fill="none">
            <circle cx="50" cy="50" r="38" stroke={accent} strokeWidth="2" strokeDasharray="4 2" />
            <circle cx="50" cy="50" r="28" stroke={accent} strokeWidth="1.5" />
            <polygon points="50,15 62,38 85,50 62,62 50,85 38,62 15,50 38,38" fill="none" stroke={accent} strokeWidth="1.5" />
            <circle cx="50" cy="50" r="10" fill={accent} fillOpacity="0.25" stroke={accent} strokeWidth="1" />
            <circle cx="50" cy="50" r="4" fill={accent} />
          </svg>
          <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: accent }}>
            {motifLabel}
          </span>
        </div>
      );
    } else if (elem === 'royal_crest') {
      const motifLabel = language === 'Hindi' ? '— शाही निमंत्रण —' : language === 'Gujarati' ? '— રાજવી નિમંત્રણ —' : '— ROYAL INVITATION —';
      return (
        <div className="flex flex-col items-center justify-center my-2 space-y-1">
          <Crown className="w-9 h-9" style={{ color: accent }} />
          <span className="text-xs font-bold tracking-widest uppercase" style={{ color: accent }}>
            {motifLabel}
          </span>
        </div>
      );
    } else if (elem === 'floral_wreath') {
      const motifLabel = language === 'Hindi' ? '— मंगल महोत्सव —' : language === 'Gujarati' ? '— મંગલ મહોત્સવ —' : '— CELEBRATION —';
      return (
        <div className="flex flex-col items-center justify-center my-2 space-y-1">
          <Flower2 className="w-9 h-9" style={{ color: accent }} />
          <span className="text-xs font-serif tracking-widest uppercase" style={{ color: accent }}>
            {motifLabel}
          </span>
        </div>
      );
    } else if (elem === 'confetti_stars') {
      const motifLabel = language === 'Hindi' ? '— आनंदोत्सव —' : language === 'Gujarati' ? '— આનંદમય ઉજવણી —' : "— LET'S CELEBRATE —";
      return (
        <div className="flex flex-col items-center justify-center my-2 space-y-1">
          <PartyPopper className="w-9 h-9" style={{ color: accent }} />
          <span className="text-xs font-sans font-bold tracking-widest uppercase" style={{ color: accent }}>
            {motifLabel}
          </span>
        </div>
      );
    } else if (elem === 'geometric_badge') {
      return (
        <div className="flex flex-col items-center justify-center my-2 space-y-1">
          <div className="w-8 h-8 rotate-45 border-2 flex items-center justify-center" style={{ borderColor: accent }}>
            <div className="w-3 h-3" style={{ backgroundColor: accent }} />
          </div>
          <span className="text-xs font-mono tracking-widest uppercase" style={{ color: accent }}>
            — • —
          </span>
        </div>
      );
    }
    return <div className="h-4" />;
  };

  // Font family helper
  const getFontFamilyClass = (font: string) => {
    switch (font) {
      case 'serif':
        return 'font-serif';
      case 'sans':
        return 'font-sans';
      case 'cursive':
        return 'font-serif italic';
      case 'display':
        return 'font-serif tracking-wide';
      default:
        return 'font-serif';
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-amber-600 via-rose-600 to-indigo-700 rounded-2xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-semibold mb-3">
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>Phase 4: AI Invitation Generator</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            AI Invitation Generator & Luxury Card Designer
          </h1>
          <p className="mt-2 text-rose-100 text-sm sm:text-base max-w-2xl leading-relaxed">
            Generate culturally authentic, multi-lingual invitations in English, Hindi, and Gujarati with Gemini AI.
            Customize luxury cards, personalize for guests, and export as PNG, PDF, or share instantly via WhatsApp.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              const savedSec = document.getElementById('saved-invitations-section');
              if (savedSec) savedSec.scrollIntoView({ behavior: 'smooth' });
            }}
            className="px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white font-medium text-sm flex items-center gap-2 transition"
          >
            <Bookmark className="w-4 h-4 text-amber-300" />
            <span>Saved Cards ({savedInvitations.length})</span>
          </button>
        </div>
      </div>

      {/* Main 2-Column Workspace: Generator Controls & Live Card Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Form Controls & Text Variations (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Card 1: Event & Guest Selector */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold">
                <Mail className="w-5 h-5 text-indigo-600" />
                <span>1. Event & Recipient Information</span>
              </div>
              {selectedGuest && (
                <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5" />
                  <span>Personalizing for {selectedGuest.full_name}</span>
                </span>
              )}
            </div>

            {/* Guest Selection Dropdown */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-indigo-600" />
                <span>Guest Personalization (Optional)</span>
              </label>
              <select
                value={selectedGuestId}
                onChange={(e) => handleGuestSelect(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
              >
                <option value="all">General Invitation (All Family & Friends)</option>
                {guests.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.full_name} ({g.category} - {g.plus_ones > 0 ? `+${g.plus_ones} Plus-Ones` : 'Single'}) — Status: {g.invitation_status}
                  </option>
                ))}
              </select>
              {selectedGuest && (
                <div className="mt-2.5 p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-800">{selectedGuest.full_name}</span>
                    <span className="text-slate-500 ml-2">({selectedGuest.category})</span>
                    <div className="text-slate-500 mt-0.5">
                      Plus Ones: <span className="font-medium text-slate-700">{selectedGuest.plus_ones}</span> • Invitation: <span className={selectedGuest.invitation_status === 'Sent' ? 'text-emerald-600 font-semibold' : 'text-slate-600'}>{selectedGuest.invitation_status}</span> • RSVP: <span className="font-medium text-slate-700">{selectedGuest.rsvp_status}</span>
                    </div>
                  </div>
                  {selectedGuest.invitation_status !== 'Sent' ? (
                    <button
                      onClick={handleConfirmMarkSent}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-xs flex items-center gap-1.5 transition shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Confirm & Mark Sent</span>
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold px-2 py-1 bg-emerald-50 rounded-lg">
                      <Check className="w-3.5 h-3.5" /> Sent
                    </span>
                  )}
                </div>
              )}
              {markingSentNotice && (
                <div className="mt-2 p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{markingSentNotice}</span>
                </div>
              )}
            </div>

            {/* Inputs Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Event Title / Name *</label>
                <input
                  type="text"
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                  placeholder="e.g. Rohan & Priya's Grand Wedding"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Host Name(s) *</label>
                <input
                  type="text"
                  value={hostNames}
                  onChange={(e) => setHostNames(e.target.value)}
                  placeholder="e.g. Mr. & Mrs. Sharma / Singhania Family"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Event Date *</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Event Time *</label>
                <input
                  type="text"
                  value={eventTime}
                  onChange={(e) => setEventTime(e.target.value)}
                  placeholder="e.g. 7:00 PM onwards"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Venue *</label>
                <input
                  type="text"
                  value={venue}
                  onChange={(e) => setVenue(e.target.value)}
                  placeholder="e.g. Grand Hyatt Ballroom"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Location / City *</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Mumbai, Maharashtra"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Additional Instructions (Optional)</label>
              <input
                type="text"
                value={additionalNotes}
                onChange={(e) => setAdditionalNotes(e.target.value)}
                placeholder="e.g. Dress code: Traditional Royal, RSVP by Dec 1st"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Language & Style Selectors */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Language</span>
                </label>
                <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl">
                  {(['English', 'Hindi', 'Gujarati'] as InvitationLanguage[]).map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setLanguage(lang)}
                      className={`py-1.5 text-xs font-medium rounded-lg transition text-center ${
                        language === lang
                          ? 'bg-white text-indigo-700 shadow-sm font-semibold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Style
                </label>
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value as InvitationStyle)}
                  className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Traditional">Traditional</option>
                  <option value="Modern">Modern</option>
                  <option value="Elegant">Elegant</option>
                  <option value="Minimalist">Minimalist</option>
                  <option value="Royal">Royal</option>
                  <option value="Fun and Casual">Fun and Casual</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Tone
                </label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Warm & Welcoming">Warm & Welcoming</option>
                  <option value="Grand & Royal">Grand & Royal</option>
                  <option value="Joyful & Upbeat">Joyful & Upbeat</option>
                  <option value="Formal & Reverent">Formal & Reverent</option>
                  <option value="Poetic & Romantic">Poetic & Romantic</option>
                </select>
              </div>
            </div>

            {/* Error Notice */}
            {generationError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{generationError}</span>
              </div>
            )}

            {/* Primary Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full py-3.5 px-4 bg-gradient-to-r from-amber-600 via-rose-600 to-indigo-600 hover:from-amber-700 hover:to-indigo-700 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-100 transition disabled:opacity-60"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Crafting 3 Multilingual Variations with AI...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300" />
                  <span>Generate 3 AI Invitation Variations</span>
                </>
              )}
            </button>
          </div>

          {/* Card 2: 3 Variations Selector & Inline Text Editor */}
          {variations.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2 text-slate-800 font-bold">
                  <FileText className="w-5 h-5 text-indigo-600" />
                  <span>2. Generated Variations ({language})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 bg-slate-100 text-slate-600 rounded-full font-medium">
                    Engine: {generationModel === 'gemini' ? 'Google Gemini 2.5' : 'Multilingual Engine'}
                  </span>
                  <button
                    onClick={handleGenerate}
                    className="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition"
                    title="Regenerate"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* 3 Variations Tabs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {variations.map((v, idx) => (
                  <button
                    key={v.variation_id}
                    onClick={() => selectVariation(idx)}
                    className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                      activeVariationIdx === idx
                        ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-xs font-bold text-indigo-600">Variation {v.variation_id}</span>
                      {activeVariationIdx === idx && (
                        <Check className="w-3.5 h-3.5 text-indigo-600" />
                      )}
                    </div>
                    <span className="text-xs font-medium text-slate-800 mt-1 line-clamp-1">
                      {v.variation_name}
                    </span>
                  </button>
                ))}
              </div>

              {/* Editable Component Fields */}
              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Personalized Salutation / Greeting
                  </label>
                  <input
                    type="text"
                    value={activeComponents.personalized_greeting}
                    onChange={(e) => handleComponentChange('personalized_greeting', e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Main Invitation Message
                  </label>
                  <textarea
                    rows={3}
                    value={activeComponents.invitation_message}
                    onChange={(e) => handleComponentChange('invitation_message', e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Event Details (Date, Time, Venue, Location)
                  </label>
                  <textarea
                    rows={2}
                    value={activeComponents.event_details}
                    onChange={(e) => handleComponentChange('event_details', e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Closing Sign-off & Host Names
                  </label>
                  <input
                    type="text"
                    value={activeComponents.closing_message}
                    onChange={(e) => handleComponentChange('closing_message', e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Copy & WhatsApp Action Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <button
                  onClick={handleCopyText}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  {copiedTextNotice ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700">Copied to Clipboard!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-600" />
                      <span>Copy Invitation Text</span>
                    </>
                  )}
                </button>

                <button
                  onClick={handleWhatsAppShare}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
                >
                  <MessageCircle className="w-3.5 h-3.5" />
                  <span>Share on WhatsApp</span>
                </button>
              </div>
            </div>
          )}

          {/* Card 3: Professional Template Carousel */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 text-slate-800 font-bold border-b border-slate-100 pb-3">
              <Palette className="w-5 h-5 text-indigo-600" />
              <span>3. Professional Card Templates (7 Styles)</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {Object.entries(TEMPLATE_PRESETS).map(([key, tmpl]) => {
                const isSelected = selectedTemplateKey === key;
                return (
                  <button
                    key={key}
                    onClick={() => applyTemplate(key)}
                    className={`p-3 rounded-xl border text-left transition relative overflow-hidden flex flex-col justify-between ${
                      isSelected
                        ? 'border-indigo-600 ring-2 ring-indigo-500/20 shadow-md'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    style={{ backgroundColor: tmpl.bg_color }}
                  >
                    <div className="flex items-center justify-between w-full mb-2">
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: tmpl.primary_color + '20',
                          color: tmpl.primary_color,
                        }}
                      >
                        {tmpl.category}
                      </span>
                      {isSelected && (
                        <span className="w-2 h-2 rounded-full bg-indigo-600" />
                      )}
                    </div>
                    <div>
                      <h4
                        className="text-xs font-bold leading-tight"
                        style={{ color: tmpl.primary_color }}
                      >
                        {tmpl.name}
                      </h4>
                      <p className="text-[10px] text-slate-500 mt-1 capitalize">
                        {tmpl.font_family} • {tmpl.border_style.replace('_', ' ')}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Card 4: Fine-Tuning Customization Controls */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 text-slate-800 font-bold border-b border-slate-100 pb-3">
              <Sliders className="w-5 h-5 text-indigo-600" />
              <span>4. Card Designer Customization</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Font Family</label>
                <select
                  value={designConfig.font_family}
                  onChange={(e) =>
                    setDesignConfig({
                      ...designConfig,
                      font_family: e.target.value as any,
                    })
                  }
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50"
                >
                  <option value="serif">Serif (Traditional)</option>
                  <option value="sans">Sans (Modern Clean)</option>
                  <option value="cursive">Cursive (Calligraphic)</option>
                  <option value="display">Display (Royal Bold)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Border Style</label>
                <select
                  value={designConfig.border_style}
                  onChange={(e) =>
                    setDesignConfig({
                      ...designConfig,
                      border_style: e.target.value as any,
                    })
                  }
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50"
                >
                  <option value="ornate_gold">Ornate Gold</option>
                  <option value="double">Double Border</option>
                  <option value="floral">Floral Accents</option>
                  <option value="dashed">Modern Cyber</option>
                  <option value="minimal">Minimal Single</option>
                  <option value="none">No Border</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Decorative Element</label>
                <select
                  value={designConfig.decorative_element}
                  onChange={(e) =>
                    setDesignConfig({
                      ...designConfig,
                      decorative_element: e.target.value as any,
                    })
                  }
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50"
                >
                  <option value="mandala_diya">Mandala & Diya</option>
                  <option value="royal_crest">Royal Crest</option>
                  <option value="floral_wreath">Floral Wreath</option>
                  <option value="confetti_stars">Confetti & Stars</option>
                  <option value="geometric_badge">Geometric Badge</option>
                  <option value="none">None</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Card Layout</label>
                <select
                  value={designConfig.layout}
                  onChange={(e) =>
                    setDesignConfig({
                      ...designConfig,
                      layout: e.target.value as any,
                    })
                  }
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50"
                >
                  <option value="centered">Centered</option>
                  <option value="framed">Framed</option>
                  <option value="split">Modern Split</option>
                  <option value="minimal">Minimalist</option>
                </select>
              </div>
            </div>

            {/* Color Palette Pickers */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-2">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Background Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={designConfig.bg_color}
                    onChange={(e) =>
                      setDesignConfig({ ...designConfig, bg_color: e.target.value })
                    }
                    className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
                  />
                  <span className="font-mono text-slate-600 uppercase">{designConfig.bg_color}</span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Primary Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={designConfig.primary_color}
                    onChange={(e) =>
                      setDesignConfig({ ...designConfig, primary_color: e.target.value })
                    }
                    className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
                  />
                  <span className="font-mono text-slate-600 uppercase">{designConfig.primary_color}</span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Accent / Gold</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={designConfig.accent_color}
                    onChange={(e) =>
                      setDesignConfig({ ...designConfig, accent_color: e.target.value })
                    }
                    className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
                  />
                  <span className="font-mono text-slate-600 uppercase">{designConfig.accent_color}</span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-600 mb-1">Text Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={designConfig.text_color}
                    onChange={(e) =>
                      setDesignConfig({ ...designConfig, text_color: e.target.value })
                    }
                    className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
                  />
                  <span className="font-mono text-slate-600 uppercase">{designConfig.text_color}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: High-Fidelity Live Card Preview & Action Bar (5 cols) */}
        <div className="lg:col-span-5 space-y-5 sticky top-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold">
                <Eye className="w-5 h-5 text-indigo-600" />
                <span>Live Card Preview</span>
              </div>
              <span className="text-xs px-2.5 py-1 bg-amber-50 text-amber-800 rounded-full font-medium">
                5 × 7 Inch Printable
              </span>
            </div>

            {/* The Visual Invitation Card */}
            <div
              ref={cardPreviewRef}
              className={`w-full min-h-[520px] rounded-2xl p-6 sm:p-8 flex flex-col justify-between transition-all duration-300 shadow-md relative overflow-hidden ${getFontFamilyClass(
                designConfig.font_family
              )}`}
              style={{
                backgroundColor: designConfig.bg_color,
                color: designConfig.text_color,
                border:
                  designConfig.border_style === 'ornate_gold'
                    ? `3px double ${designConfig.accent_color}`
                    : designConfig.border_style === 'double'
                    ? `4px double ${designConfig.primary_color}`
                    : designConfig.border_style === 'dashed'
                    ? `2px dashed ${designConfig.accent_color}`
                    : designConfig.border_style === 'minimal'
                    ? `1px solid ${designConfig.accent_color}`
                    : 'none',
              }}
            >
              {/* Inner Decorative Border Frame */}
              <div
                className="absolute inset-2 pointer-events-none rounded-xl"
                style={{
                  border: `1px solid ${designConfig.primary_color}30`,
                }}
              />

              {/* Top Motif */}
              <div>{renderCardMotif()}</div>

              {/* Center Content */}
              <div className="text-center space-y-4 my-auto relative z-10">
                {/* Event Title */}
                <h2
                  className="text-xl sm:text-2xl font-bold tracking-tight leading-tight px-2"
                  style={{ color: designConfig.primary_color }}
                >
                  {eventName || 'Your Celebration Title'}
                </h2>

                {/* Greeting */}
                {activeComponents.personalized_greeting && (
                  <p
                    className="text-sm sm:text-base font-medium italic"
                    style={{ color: designConfig.primary_color }}
                  >
                    {activeComponents.personalized_greeting}
                  </p>
                )}

                {/* Main Message */}
                <p
                  className="text-xs sm:text-sm leading-relaxed px-2 text-slate-700"
                  style={{ color: designConfig.text_color }}
                >
                  {activeComponents.invitation_message ||
                    'We request the pleasure of your company to celebrate this wonderful milestone with us.'}
                </p>

                {/* Highlight Box for Details */}
                <div
                  className="p-3.5 rounded-xl border max-w-sm mx-auto shadow-sm"
                  style={{
                    backgroundColor:
                      designConfig.bg_color === '#0F172A' || designConfig.bg_color === '#111827'
                        ? '#1E293B'
                        : '#FFFFFF',
                    borderColor: designConfig.accent_color,
                  }}
                >
                  <p
                    className="text-[10px] font-bold tracking-wider uppercase mb-1"
                    style={{ color: designConfig.primary_color }}
                  >
                    Event Details
                  </p>
                  <p
                    className="text-xs leading-snug whitespace-pre-line"
                    style={{ color: designConfig.text_color }}
                  >
                    {activeComponents.event_details ||
                      `${eventDate || 'Date TBD'} • ${eventTime || '7:00 PM'}\n${venue || 'Venue'}, ${location || 'Location'}`}
                  </p>
                </div>
              </div>

              {/* Host Sign-off */}
              <div className="text-center pt-4 relative z-10">
                <p
                  className="text-xs sm:text-sm font-semibold italic whitespace-pre-line"
                  style={{ color: designConfig.primary_color }}
                >
                  {activeComponents.closing_message || `With warm regards,\n${hostNames || 'The Host Family'}`}
                </p>
              </div>
            </div>

            {/* Action Buttons: Download PNG, Download PDF, WhatsApp, Save */}
            <div className="space-y-2 pt-2">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleDownloadPng}
                  disabled={isExportingPng}
                  className="py-2.5 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition shadow-sm disabled:opacity-50"
                >
                  <ImageIcon className="w-4 h-4 text-amber-400" />
                  <span>{isExportingPng ? 'Rendering PNG...' : 'Download PNG'}</span>
                </button>

                <button
                  onClick={handleDownloadPdf}
                  disabled={isExportingPdf}
                  className="py-2.5 px-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition shadow-sm disabled:opacity-50"
                >
                  <FileText className="w-4 h-4 text-white" />
                  <span>{isExportingPdf ? 'Exporting PDF...' : 'Download PDF'}</span>
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleWhatsAppShare}
                  className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>Send WhatsApp</span>
                </button>

                <button
                  onClick={handleSaveInvitation}
                  disabled={isSaving}
                  className="py-2.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition shadow-sm disabled:opacity-50"
                >
                  <Bookmark className="w-4 h-4" />
                  <span>{isSaving ? 'Saving...' : 'Save Invitation'}</span>
                </button>
              </div>

              {saveSuccessNotice && (
                <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{saveSuccessNotice}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Saved Invitations Ledger / Gallery */}
      <div id="saved-invitations-section" className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2.5 text-slate-800 font-bold text-lg">
            <Bookmark className="w-5 h-5 text-indigo-600" />
            <span>Saved Invitations Gallery ({savedInvitations.length})</span>
          </div>
          <span className="text-xs text-slate-500">
            Persistent records linked with Eventify AI database
          </span>
        </div>

        {savedInvitations.length === 0 ? (
          <div className="text-center py-12 text-slate-400 space-y-2">
            <Mail className="w-12 h-12 mx-auto text-slate-300 stroke-[1.5]" />
            <p className="text-sm font-medium text-slate-600">No saved invitations yet</p>
            <p className="text-xs text-slate-400">
              Generate and customize an invitation above, then click "Save Invitation" to store it here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {savedInvitations.map((inv) => (
              <div
                key={inv.id}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 hover:bg-slate-50 transition flex flex-col justify-between space-y-3 shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                      {inv.language} • {inv.style}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-800 mt-2 line-clamp-1">{inv.title}</h4>
                  {inv.guest_name && (
                    <p className="text-xs text-indigo-600 font-medium flex items-center gap-1 mt-0.5">
                      <User className="w-3 h-3" />
                      <span>Recipient: {inv.guest_name}</span>
                    </p>
                  )}
                  <p className="text-xs text-slate-600 mt-2 line-clamp-2 italic">
                    "{inv.text_components.invitation_message}"
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-200/80">
                  <button
                    onClick={() => handleLoadSaved(inv)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                  >
                    <span>Load into Editor</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  <div className="flex items-center gap-2">
                    <a
                      href={getSavedInvitationPdfUrl(inv.id)}
                      download
                      className="p-1.5 text-slate-500 hover:text-rose-600 rounded-lg hover:bg-white transition"
                      title="Download PDF"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => handleDeleteSaved(inv.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-white transition"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
export default InvitationsTab;
