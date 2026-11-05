import re
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from pydantic import BaseModel, Field

from .schemas import (
    FullEventPlan,
    BudgetSummary,
    BudgetItem,
    BudgetAnalysis,
    BudgetOptimizationResponse,
    CategoryOptimization,
    OptimizationExplanation,
    DuplicateCategoryWarning,
    CategoryMergeSuggestion,
    CategoryTaxonomyAnalysis,
)
from .gemini_client import GeminiClient, sanitize_user_input
from .config import GEMINI_MODEL

logger = logging.getLogger(__name__)

# Strict Decimal precision constant
CENT = Decimal("0.01")
PERCENT = Decimal("100.00")


def to_decimal(val: Any) -> Decimal:
    """Converts a number, string, or Decimal to a precise 2-decimal-place Decimal using ROUND_HALF_UP."""
    if isinstance(val, Decimal):
        return val.quantize(CENT, rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_inr(
    amount: Any,
    include_symbol: bool = True,
    decimals: Optional[int] = None,
    symbol: str = "₹",
) -> str:
    """
    Format a number using the Indian numbering system (e.g. 5000000 -> "₹50,00,000").
    - If decimals is None, whole numbers omit .00 while decimal values show 2 decimal places.
    - Accurately groups the last 3 digits, then pairs of 2 digits (Lakhs and Crores).
    """
    try:
        amt = float(amount)
    except (ValueError, TypeError):
        return f"{symbol}0" if include_symbol else "0"

    is_neg = amt < 0
    amt = abs(amt)

    if decimals is None:
        decimals = 0 if amt == int(amt) else 2

    if decimals > 0:
        formatted_dec = f"{amt:.{decimals}f}"
        int_part, dec_part = formatted_dec.split(".")
    else:
        int_part = str(int(round(amt)))
        dec_part = ""

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        grouped = ",".join(groups) + "," + last_three

    res = f"{grouped}.{dec_part}" if decimals > 0 and dec_part else grouped
    sign = "-" if is_neg else ""
    sym = (symbol + " ") if (include_symbol and symbol and symbol not in ["₹", "$", "€", "£"]) else (symbol if include_symbol else "")
    return f"{sign}{sym}{res}"


# =====================================================================
# STANDARDIZED BUDGET CATEGORY TAXONOMY & CLASSIFICATION
# =====================================================================

STANDARD_CATEGORIES: List[str] = [
    "Venue & Accommodation",
    "Catering & Beverages",
    "Decoration & Floral",
    "Photography & Videography",
    "Entertainment & Music",
    "Attire & Styling",
    "Makeup & Beauty",
    "Invitations & Stationery",
    "Logistics & Transportation",
    "Rituals & Religious Services",
    "Guest Management",
    "Contingency & Emergency Fund",
    "Miscellaneous",
]

DEFAULT_CLASSIFICATIONS: Dict[str, str] = {
    "Venue & Accommodation": "essential",
    "Catering & Beverages": "essential",
    "Decoration & Floral": "important",
    "Photography & Videography": "important",
    "Entertainment & Music": "optional",
    "Attire & Styling": "important",
    "Makeup & Beauty": "optional",
    "Invitations & Stationery": "optional",
    "Logistics & Transportation": "essential",
    "Rituals & Religious Services": "important",
    "Guest Management": "important",
    "Contingency & Emergency Fund": "essential",
    "Miscellaneous": "optional",
}

# Domain keywords for single-domain identification and multi-domain collision detection
DOMAIN_KEYWORDS: Dict[str, Set[str]] = {
    "Venue & Accommodation": {
        "venue", "lodging", "hotel", "resort", "accommodation", "stay", "room", "rooms",
        "hall", "banquet", "palace", "space rental", "grounds & permits", "grounds"
    },
    "Catering & Beverages": {
        "catering", "food", "beverage", "beverages", "drink", "drinks", "bar", "cocktail",
        "cocktails", "buffet", "dining", "cake", "refreshments", "meals"
    },
    "Decoration & Floral": {
        "decor", "decoration", "floral", "flowers", "mandap", "lighting", "balloons",
        "centerpieces", "signage", "banners", "florals"
    },
    "Photography & Videography": {
        "photography", "videography", "photos", "videos", "cinematography", "drone",
        "albums", "photographer", "photo", "video"
    },
    "Entertainment & Music": {
        "entertainment", "music", "dj", "band", "orchestra", "performers", "live music",
        "sound", "sound & av", "av equipment", "audio", "activities", "stage"
    },
    "Attire & Styling": {
        "attire", "wardrobe", "dress", "sherwani", "lehenga", "suit", "styling", "clothing",
        "outfits", "bridal wear", "groom wear"
    },
    "Makeup & Beauty": {
        "makeup", "beauty", "hair", "salon", "grooming", "mehendi", "henna"
    },
    "Invitations & Stationery": {
        "invitations", "stationery", "invites", "cards", "save the date", "programs",
        "printing", "invitation"
    },
    "Logistics & Transportation": {
        "logistics", "transportation", "transport", "travel", "fleet", "cabs", "shuttle",
        "valet", "buses", "cars"
    },
    "Rituals & Religious Services": {
        "rituals", "religious", "puja", "priest", "pandit", "ceremony", "vedic rituals",
        "havan", "samagri", "sangeet night"
    },
    "Guest Management": {
        "guest", "guests", "rsvp", "hampers", "return gifts", "favors", "goodie bags",
        "hospitality", "badges"
    },
    "Contingency & Emergency Fund": {
        "contingency", "emergency", "reserve", "buffer", "emergency fund", "contingency fund"
    },
    "Miscellaneous": {
        "miscellaneous", "misc", "other", "general", "extra", "incidentals", "unplanned"
    },
}


def map_category_to_canonical(name: str) -> Tuple[Optional[str], float, bool]:
    """
    Maps an arbitrary category name to a standardized category taxonomy.
    Returns: (canonical_name, confidence_score, is_compound)

    Guarantees:
    1. Exact canonical matches return (canonical, 1.0, False).
    2. Multi-domain / compound categories (e.g. "Attire, Makeup & Priest")
       matching 2+ distinct canonical domains return (None, 0.0, True),
       preventing arbitrary or destructive automatic merging.
    3. Confident single-domain matches return (canonical, score, False).
    4. Unmatched / custom categories return (None, 0.0, False).
    """
    raw = (name or "").strip()
    if not raw:
        return None, 0.0, False

    low = raw.lower()

    # 1. Exact match with any canonical category
    for std in STANDARD_CATEGORIES:
        if low == std.lower():
            return std, 1.0, False

    # 2. Multi-domain collision check
    matched_domains: Set[str] = set()

    for std, kw_set in DOMAIN_KEYWORDS.items():
        for kw in kw_set:
            # Check whole word or phrase match
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, low):
                matched_domains.add(std)
                break

    # If the category spans multiple distinct domains (e.g. "Attire, Makeup & Priest"),
    # it represents genuinely distinct expense types and MUST NOT be auto-merged!
    if len(matched_domains) > 1:
        return None, 0.0, True

    # 3. Confident single-domain match
    if len(matched_domains) == 1:
        canonical = next(iter(matched_domains))
        return canonical, 0.90, False

    # 4. Unknown / custom category
    return None, 0.0, False


def detect_duplicate_and_overlapping_categories(
    items: List[BudgetItem],
    currency: str = "INR",
) -> Tuple[List[DuplicateCategoryWarning], List[CategoryMergeSuggestion]]:
    """
    Scans budget items to detect:
    1. Exact duplicate category names.
    2. Similar/equivalent category names mapping to the same canonical category.
    3. Overlapping spending categories.
    4. Suspicious duplicate allocations.
    """
    warnings: List[DuplicateCategoryWarning] = []
    suggestions: List[CategoryMergeSuggestion] = []

    # 1. Exact duplicate names
    name_groups: Dict[str, List[BudgetItem]] = {}
    for it in items:
        k = it.category.strip().lower()
        name_groups.setdefault(k, []).append(it)

    for k, group in name_groups.items():
        if len(group) > 1:
            cat_name = group[0].category
            combined_alloc = sum(to_decimal(i.allocated_amount) for i in group)
            combined_pct = sum(to_decimal(i.percentage) for i in group)
            combined_spent = sum(to_decimal(i.actual_spent) for i in group)
            mapped, _, _ = map_category_to_canonical(cat_name)
            canonical = mapped or cat_name

            sug = CategoryMergeSuggestion(
                source_category_ids=[i.id for i in group],
                source_categories=[i.category for i in group],
                canonical_category=canonical,
                combined_allocation=float(combined_alloc),
                combined_percentage=float(combined_pct),
                combined_spent=float(combined_spent),
                rationale=f"Exact duplicate category '{cat_name}' is entered {len(group)} times. Merging combines their allocations to {currency} {float(combined_alloc):,.2f}.",
                confidence=1.0,
            )
            suggestions.append(sug)
            warnings.append(
                DuplicateCategoryWarning(
                    warning_type="exact_duplicate",
                    severity="warning",
                    message=f"Duplicate category detected: '{cat_name}' appears {len(group)} times in your budget.",
                    affected_categories=[i.category for i in group],
                    suggested_merge=sug,
                )
            )

    # 2. Similar / Overlapping categories mapping to the same canonical category
    canonical_groups: Dict[str, List[BudgetItem]] = {}
    for it in items:
        mapped, conf, is_compound = map_category_to_canonical(it.category)
        if mapped and not is_compound:
            canonical_groups.setdefault(mapped, []).append(it)

    for canonical, group in canonical_groups.items():
        distinct_names = set(i.category.strip().lower() for i in group)
        if len(distinct_names) > 1:
            combined_alloc = sum(to_decimal(i.allocated_amount) for i in group)
            combined_pct = sum(to_decimal(i.percentage) for i in group)
            combined_spent = sum(to_decimal(i.actual_spent) for i in group)
            names_display = [i.category for i in group]

            sug = CategoryMergeSuggestion(
                source_category_ids=[i.id for i in group],
                source_categories=names_display,
                canonical_category=canonical,
                combined_allocation=float(combined_alloc),
                combined_percentage=float(combined_pct),
                combined_spent=float(combined_spent),
                rationale=f"Categories ({', '.join(set(names_display))}) represent equivalent expenses under standard '{canonical}'. Merging unifies them into a single allocation of {currency} {float(combined_alloc):,.2f}.",
                confidence=0.90,
            )
            if not any(w.message.startswith(f"Overlapping categories detected under '{canonical}'") for w in warnings):
                suggestions.append(sug)
                warnings.append(
                    DuplicateCategoryWarning(
                        warning_type="similar_category",
                        severity="warning",
                        message=f"Overlapping categories detected under '{canonical}': {', '.join(set(names_display))}. Consider reviewing suggested merge.",
                        affected_categories=list(set(names_display)),
                        suggested_merge=sug,
                    )
                )

    # 3. Duplicate allocation amounts with similar names
    for idx_a, a in enumerate(items):
        for b in items[idx_a + 1:]:
            if a.category.lower() != b.category.lower() and a.allocated_amount > 0 and a.allocated_amount == b.allocated_amount:
                words_a = set(re.findall(r"\b[a-z]{3,}\b", a.category.lower()))
                words_b = set(re.findall(r"\b[a-z]{3,}\b", b.category.lower()))
                if words_a & words_b:
                    warnings.append(
                        DuplicateCategoryWarning(
                            warning_type="duplicate_amount",
                            severity="info",
                            message=f"Categories '{a.category}' and '{b.category}' share identical allocations of {currency} {a.allocated_amount:,.2f}.",
                            affected_categories=[a.category, b.category],
                            suggested_merge=None,
                        )
                    )

    return warnings, suggestions


def normalize_budget_categories(
    items: List[BudgetItem],
    total_budget: float,
    approved_canonical_merges: Optional[List[str]] = None,
    currency: str = "INR",
    return_rename_map: bool = False,
) -> Union[List[BudgetItem], Tuple[List[BudgetItem], Dict[str, str]]]:
    """
    Standardizes budget category taxonomy while preserving total budget down to 0.00.
    - Preserves custom categories and compound categories as-is.
    - If approved_canonical_merges is None, automatically detects all suggested merges.
    - If approved_canonical_merges is provided, merges only matching canonical categories.
    - Merges duplicate categories deterministically combining allocations and spending.
    - Sets canonical_category and default classifications.
    - Guarantees total budget and allocation are unchanged (100% allocation invariant).
    - Can return rename_map of source category names -> canonical category.
    """
    D_total_budget = to_decimal(total_budget)
    if approved_canonical_merges is None:
        _, suggestions = detect_duplicate_and_overlapping_categories(items, currency)
        approved_set = set(s.canonical_category.lower().strip() for s in suggestions)
    else:
        approved_set = set(c.lower().strip() for c in approved_canonical_merges)

    # Group items by merge destination
    merged_buckets: Dict[str, List[BudgetItem]] = {}

    for item in items:
        mapped, conf, is_compound = map_category_to_canonical(item.category)
        if mapped and not is_compound and mapped.lower() in approved_set:
            bucket_key = f"canonical_{mapped.lower()}"
        else:
            bucket_key = f"item_{item.id}"
        merged_buckets.setdefault(bucket_key, []).append(item)

    normalized_items: List[BudgetItem] = []
    rename_map: Dict[str, str] = {}

    for bucket_key, group in merged_buckets.items():
        if len(group) == 1:
            it = group[0]
            mapped, conf, is_compound = map_category_to_canonical(it.category)
            canonical = mapped if (mapped and not is_compound) else None
            cls_name = it.classification or (DEFAULT_CLASSIFICATIONS.get(canonical, "custom") if canonical else "custom")
            if it.is_contingency:
                cls_name = "essential"

            normalized_items.append(
                BudgetItem(
                    id=it.id,
                    category=it.category,
                    weight=it.weight,
                    percentage=it.percentage,
                    allocated_amount=it.allocated_amount,
                    actual_spent=it.actual_spent,
                    is_contingency=it.is_contingency,
                    is_mandatory=it.is_mandatory,
                    notes=it.notes,
                    canonical_category=canonical,
                    classification=cls_name,
                    is_protected=bool(it.is_protected),
                )
            )
        else:
            # Merged group
            mapped, _, _ = map_category_to_canonical(group[0].category)
            canonical_title = mapped or group[0].category
            combined_alloc = sum(to_decimal(i.allocated_amount) for i in group)
            combined_spent = sum(to_decimal(i.actual_spent) for i in group)
            is_cont = any(i.is_contingency for i in group)
            is_mand = any(i.is_mandatory for i in group)
            is_prot = any(i.is_protected for i in group)

            for i in group:
                rename_map[i.category.strip().lower()] = canonical_title

            best_id_item = next((i for i in group if i.category.strip().lower() == canonical_title.strip().lower()), group[0])

            source_detail = ", ".join(f"'{i.category}' ({currency} {i.allocated_amount:,.2f})" for i in group)
            combined_notes = f"Standardized merge of: {source_detail}."

            normalized_items.append(
                BudgetItem(
                    id=best_id_item.id,
                    category=canonical_title,
                    weight=sum(i.weight for i in group),
                    percentage=sum(i.percentage for i in group),
                    allocated_amount=float(combined_alloc),
                    actual_spent=float(combined_spent),
                    is_contingency=is_cont,
                    is_mandatory=is_mand,
                    notes=combined_notes,
                    canonical_category=canonical_title,
                    classification="essential" if is_cont else DEFAULT_CLASSIFICATIONS.get(canonical_title, "important"),
                    is_protected=is_prot,
                )
            )

    # Reconcile exact percentages and total amounts with Decimal
    D_allocated_sum = sum(to_decimal(i.allocated_amount) for i in normalized_items)
    diff = D_total_budget - D_allocated_sum
    if diff != Decimal("0.00") and normalized_items:
        non_con = [i for i in normalized_items if not i.is_contingency]
        largest = max(non_con or normalized_items, key=lambda x: x.allocated_amount)
        new_amt = to_decimal(largest.allocated_amount) + diff
        largest.allocated_amount = float(new_amt)

    # Reconcile percentages
    for it in normalized_items:
        if D_total_budget > Decimal("0.00"):
            pct = ((to_decimal(it.allocated_amount) / D_total_budget) * PERCENT).quantize(CENT, rounding=ROUND_HALF_UP)
            it.percentage = float(pct)

    pct_diff = PERCENT - sum(to_decimal(i.percentage) for i in normalized_items)
    if pct_diff != Decimal("0.00") and normalized_items:
        non_con = [i for i in normalized_items if not i.is_contingency]
        largest = max(non_con or normalized_items, key=lambda x: x.allocated_amount)
        largest.percentage = float(to_decimal(largest.percentage) + pct_diff)

    if return_rename_map:
        return normalized_items, rename_map
    return normalized_items


# =====================================================================
# STEP 1: NATURAL LANGUAGE & CURRENCY INTENT EXTRACTION
# =====================================================================

CURRENCY_PREFIX = r"(?:(?:₹|rs\.?|inr|\$|€|rupees?\.?)\s*)"
AMOUNT_NUM_PATTERN = r"(?:\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
UNIT_SUFFIX = r"(?:\s*(?:crores?|crs?\b|cr\b|lakhs?|lacs?|lac\b|l\b|millions?|m\b|thousands?|k\b|rupees?\.?))"
AMOUNT_PATTERN = rf"(?:{CURRENCY_PREFIX}?{AMOUNT_NUM_PATTERN}{UNIT_SUFFIX}?(?!\d))"


class BudgetOptimizationSpec(BaseModel):
    """Structured specification of the user's financial optimization intent."""
    intent_type: str = "general"
    target_revised_budget: Optional[float] = None
    target_savings_amount: Optional[float] = None
    target_savings_percentage: Optional[float] = None
    protected_categories: List[str] = Field(default_factory=list)
    prioritized_categories: List[str] = Field(default_factory=list)
    category_percentage_reductions: Dict[str, float] = Field(default_factory=dict)
    category_boosts: Dict[str, float] = Field(default_factory=dict)
    reallocate_from: Optional[str] = None
    reallocate_to: Optional[str] = None
    is_feasible: bool = True
    infeasibility_reason: Optional[str] = None


def parse_currency_amount(text: str) -> Optional[float]:
    """
    Parses Indian and International currency expressions from natural language.
    Supports:
      - Plain numbers: 5000000 -> 50,00,000, 500000 -> 5,00,000, 50000 -> 50,000
      - Indian numbering: ₹2,00,000, 25,00,000, 50,00,000, 10,00,000, 7,00,000
      - International numbering: 5,000,000, 500,000, 50,000
      - Indian units: 50 lakh, 50 lakhs, 2.5 lakh, 2 lac, 20 lac, 1 crore, 1.5 cr, 1.5 crore
      - International units: 5 million, 2.5m, 50k, 50 thousand
      - Currency prefixes and suffixes: ₹, Rs., INR, $, €, rupees
    """
    t = text.lower().strip()

    # 1. Crore / Cr: e.g. "1.5 crore", "2 cr", "₹1 crore", "1.5cr"
    cr_match = re.search(r"(?:₹|rs\.?|inr|\$|€|rupees?\.?)?\s*(\d+(?:\.\d+)?)\s*(?:crores?|crs?\b|cr\b)", t)
    if cr_match:
        return float(cr_match.group(1)) * 10_000_000.0

    # 2. Lakh / Lac: e.g. "50 lakh", "50 lakhs", "2.5 lakh", "2 lac", "20 lac", "2 l", "2lakh"
    lakh_match = re.search(r"(?:₹|rs\.?|inr|\$|€|rupees?\.?)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|lac\b|l\b)", t)
    if lakh_match:
        return float(lakh_match.group(1)) * 100_000.0

    # 3. Million / M: e.g. "5 million", "2.5m", "2 million"
    m_match = re.search(r"(?:₹|rs\.?|inr|\$|€|rupees?\.?)?\s*(\d+(?:\.\d+)?)\s*(?:millions?|m\b)", t)
    if m_match:
        return float(m_match.group(1)) * 1_000_000.0

    # 4. Thousand / K: e.g. "50k", "50 thousand"
    k_match = re.search(r"(?:₹|rs\.?|inr|\$|€|rupees?\.?)?\s*(\d+(?:\.\d+)?)\s*(?:thousands?|k\b)", t)
    if k_match:
        return float(k_match.group(1)) * 1_000.0

    # 5. Comma-separated or standard digits: e.g. "₹50,00,000", "5,000,000", "5000000", "500000", "50000"
    num_match = re.search(
        r"(?:(?:₹|rs\.?|inr|\$|€|rupees?\.?)\s*)?(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\d)",
        t
    )
    if num_match:
        raw = num_match.group(1).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return None

    return None


def extract_budget_intent(
    user_prompt: str,
    original_budget: float,
    plan_categories: Optional[List[str]] = None,
) -> BudgetOptimizationSpec:
    """
    Deterministic extraction of user's financial intent, target numbers,
    protected items, priorities, and feasibility from natural language.
    """
    spec = BudgetOptimizationSpec()
    lower = user_prompt.lower().strip()
    cats = plan_categories or [
        "Venue & Lodging", "Catering & Bar", "Decor & Florals", "Photography & Video",
        "Entertainment & Music", "Attire & Beauty", "Invitations & Stationery", "Contingency"
    ]
    cats_lower = {c.lower(): c for c in cats}

    def find_matching_cat(keyword: str) -> Optional[str]:
        kw = keyword.lower().strip()
        for cl, c_orig in cats_lower.items():
            if kw in cl or cl in kw:
                return c_orig
        synonyms = {
            "food": "Catering", "cater": "Catering", "drink": "Catering", "bar": "Catering",
            "venue": "Venue", "hall": "Venue", "hotel": "Venue", "resort": "Venue", "lodging": "Venue",
            "photo": "Photography", "video": "Photography", "camera": "Photography",
            "music": "Entertainment", "dj": "Entertainment", "band": "Entertainment", "entertainment": "Entertainment",
            "floral": "Decor", "flower": "Decor", "decoration": "Decor", "decor": "Decor",
        }
        for syn_k, syn_target in synonyms.items():
            if syn_k in kw:
                for cl, c_orig in cats_lower.items():
                    if syn_target.lower() in cl:
                        return c_orig
        return None

    # 1. Detect Protected Categories from natural language
    protect_patterns = [
        r"without\s+compromising\s+(?:the\s+)?([a-z\s]+?)(?:$|\.|\,)",
        r"keep\s+([a-z\s]+?)\s+(?:quality\s+)?(?:high|intact|priority|top|safe|uncompromised)",
        r"(?:do\s*n['o]t|don['o]t|never)\s+(?:reduce|cut|touch|decrease|lower)\s+(?:the\s+)?([a-z\s]+?)(?:expenses|budget|costs|$|\.|\,)",
        r"(?:protect|preserve|safeguard|maintain)\s+(?:the\s+)?([a-z\s]+?)(?:expenses|budget|costs|$|\.|\,)",
    ]
    for p in protect_patterns:
        for match in re.finditer(p, lower):
            target_str = match.group(1).strip()
            cat = find_matching_cat(target_str)
            if cat and cat not in spec.protected_categories:
                spec.protected_categories.append(cat)

    # 2. Detect Category Boosts & Prioritized Categories from multi-number and reallocation inputs
    boost_patterns = [
        rf"(?:allocate|give|add)\s+({AMOUNT_PATTERN})\s+(?:more\s+)?to\s+([a-z\s&]+)",
        rf"increase\s+([a-z\s&]+?)\s+(?:budget\s+)?by\s+({AMOUNT_PATTERN})",
        rf"spend\s+({AMOUNT_PATTERN})\s+more\s+on\s+([a-z\s&]+)",
    ]
    for bp in boost_patterns:
        bm = re.search(bp, lower)
        if bm:
            if "increase" in bp:
                cat_raw = bm.group(1)
                amt_raw = bm.group(2)
            else:
                amt_raw = bm.group(1)
                cat_raw = bm.group(2)
            parsed_amt = parse_currency_amount(amt_raw)
            cat_obj = find_matching_cat(cat_raw)
            if cat_obj and parsed_amt:
                spec.category_boosts[cat_obj] = parsed_amt
                if cat_obj not in spec.prioritized_categories:
                    spec.prioritized_categories.append(cat_obj)

    # Detect Prioritized Categories
    prioritize_patterns = [
        r"prioritize\s+([a-z\s&]+?)(?:$|\.|\,|and\s+reduce)",
        r"focus\s+on\s+([a-z\s&]+?)(?:$|\.|\,)",
    ]
    for p in prioritize_patterns:
        m = re.search(p, lower)
        if m:
            raw_cats = m.group(1).replace("and", ",").split(",")
            for rc in raw_cats:
                cat = find_matching_cat(rc.strip())
                if cat and cat not in spec.prioritized_categories:
                    spec.prioritized_categories.append(cat)

    # 3. Detect Reallocation
    realloc_match = re.search(r"reallocate\s+(?:unused\s+)?([a-z\s]+?)\s+(?:expenses?\s+)?to\s+([a-z\s]+)", lower)
    if realloc_match:
        from_cat = find_matching_cat(realloc_match.group(1).strip())
        to_cat = find_matching_cat(realloc_match.group(2).strip())
        if from_cat and to_cat:
            spec.intent_type = "reallocation"
            spec.reallocate_from = from_cat
            spec.reallocate_to = to_cat
            spec.target_revised_budget = original_budget
            spec.target_savings_amount = 0.0

    # 4. Detect Category-Specific Reductions
    cat_pct_match = re.search(r"(?:reduce|cut|lower|decrease|trim)\s+([a-z\s]+?)\s+(?:expenses?\s+|budget\s+)?by\s+(\d+(?:\.\d+)?)\s*%", lower)
    if cat_pct_match:
        cat_candidate = find_matching_cat(cat_pct_match.group(1).strip())
        pct = float(cat_pct_match.group(2))
        if cat_candidate and 0 < pct < 100:
            spec.category_percentage_reductions[cat_candidate] = pct
            spec.intent_type = "category_reduction"

    # 5. Detect Overall Percentage Savings
    if not spec.category_percentage_reductions:
        pct_match = re.search(r"(?:save|reduce|cut|lower|decrease|trim)\s+(?:.*?budget\s+)?(?:by\s+)?(\d+(?:\.\d+)?)\s*%", lower)
        if pct_match:
            pct_val = float(pct_match.group(1))
            if pct_val <= 0 or pct_val >= 100:
                spec.is_feasible = False
                spec.infeasibility_reason = f"Savings percentage of {pct_val}% is invalid. Please specify a percentage between 1% and 99%."
                return spec
            spec.intent_type = "percentage_reduction"
            spec.target_savings_percentage = pct_val
            spec.target_savings_amount = round((pct_val / 100.0) * original_budget, 2)
            spec.target_revised_budget = round(original_budget - spec.target_savings_amount, 2)
            return spec

    # 6. Detect Target Revised Budget
    target_to_match = re.search(
        r"(?:(?:reduce|lower|cut|decrease|bring|drop|change|adjust)\s+(?:.*?budget\s+)?(?:down\s+)?to\s+|"
        r"(?:set|make|limit|fix|keep)\s+(?:.*?budget\s+)?(?:at|to|within|under)\s+|"
        r"(?:target|revised|new|total)\s+budget\s+(?:is|of|to|should be|:)?\s*)"
        rf"({AMOUNT_PATTERN})",
        lower,
    )
    if target_to_match:
        target_budget = parse_currency_amount(target_to_match.group(1))
        if target_budget is not None:
            if target_budget > original_budget:
                spec.is_feasible = False
                spec.target_revised_budget = original_budget
                spec.target_savings_amount = 0.0
                spec.infeasibility_reason = (
                    f"The requested revised budget of {format_inr(target_budget)} exceeds the original budget of {format_inr(original_budget)}. "
                    "The AI Smart Budget Optimizer reduces or reallocates expenses to generate savings. "
                    "To increase your overall budget, please update the event budget directly in Event Settings."
                )
                return spec
            if target_budget <= 0:
                spec.is_feasible = False
                spec.infeasibility_reason = "The requested revised budget must be greater than zero."
                return spec
            spec.intent_type = "target_budget"
            spec.target_revised_budget = target_budget
            spec.target_savings_amount = round(original_budget - target_budget, 2)
            return spec

    # 7. Detect Savings Amount
    savings_match = re.search(
        r"(?:(?:reduce|lower|cut|decrease|trim|slash)\s+(?:.*?budget\s+)?by\s+|"
        r"(?:save|cut|trim|shave)\s+(?:(?:an?\s+)?extra\s+)?|"
        r"savings?\s+(?:of|target)?\s*)"
        rf"({AMOUNT_PATTERN})",
        lower,
    )
    if savings_match:
        savings = parse_currency_amount(savings_match.group(1))
        if savings is not None and savings > 0:
            if savings >= original_budget:
                spec.is_feasible = False
                spec.infeasibility_reason = (
                    f"The requested savings of {format_inr(savings)} exceeds or equals the original budget of {format_inr(original_budget)}. "
                    "Please specify a feasible savings amount."
                )
                return spec
            spec.intent_type = "savings_amount"
            spec.target_savings_amount = savings
            spec.target_revised_budget = round(original_budget - savings, 2)
            return spec

    # 8. Direct Amount Fallback (e.g. user prompt is simply "5000000" or "₹50,00,000" or "50 lakh")
    if not spec.target_revised_budget and not spec.target_savings_amount:
        direct_amt = parse_currency_amount(lower)
        if direct_amt is not None and direct_amt > 0:
            if direct_amt > original_budget:
                spec.is_feasible = False
                spec.target_revised_budget = original_budget
                spec.target_savings_amount = 0.0
                spec.infeasibility_reason = (
                    f"The requested revised budget of {format_inr(direct_amt)} exceeds the original budget of {format_inr(original_budget)}. "
                    "The AI Smart Budget Optimizer reduces or reallocates expenses to generate savings. "
                    "To increase your overall budget, please update the event budget directly in Event Settings."
                )
                return spec
            spec.intent_type = "target_budget"
            spec.target_revised_budget = direct_amt
            spec.target_savings_amount = round(original_budget - direct_amt, 2)
            return spec

    return spec


# =====================================================================
# STEP 3 & 4: DETERMINISTIC FINANCIAL BALANCING USING PYTHON DECIMAL
# =====================================================================

def balance_budget_allocations_decimal(
    orig_items: List[BudgetItem],
    revised_total_budget: float,
    protected_categories: List[str],
    prioritized_categories: List[str],
    category_percentage_reductions: Dict[str, float],
    suggested_weights: Optional[Dict[str, float]] = None,
    reallocate_from: Optional[str] = None,
    reallocate_to: Optional[str] = None,
    contingency_pct: float = 8.0,
    category_boosts: Optional[Dict[str, float]] = None,
) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
    """
    Independent Financial Calculation Engine powered by Python Decimal:
    1. Guarantees 0 floating-point rounding errors (100% Decimal math).
    2. Validates budget feasibility: Minimum Protected Budget <= revised_total_budget.
    3. Preserves 100% of protected category allocations.
    4. Enforces non-negative allocations.
    5. Prioritizes essential over optional expenses.
    6. Ensures exact sum down to 0.01.
    """
    D_revised = to_decimal(revised_total_budget)
    D_orig_total = sum(to_decimal(i.allocated_amount) for i in orig_items)
    is_reduction = D_revised < D_orig_total

    protected_lower = set(c.lower().strip() for c in protected_categories)
    prioritized_lower = set(c.lower().strip() for c in prioritized_categories)

    def is_item_protected(it: BudgetItem) -> bool:
        if it.is_contingency:
            c_low = it.category.lower().strip()
            return any(p in c_low or c_low in p for p in protected_lower)
        if it.is_protected:
            return True
        c_low = it.category.lower().strip()
        canon_low = (it.canonical_category or "").lower().strip()
        return any(p == c_low or p in c_low or (canon_low and (p == canon_low or p in canon_low)) for p in protected_lower)

    # 1. Identify protected items and calculate Minimum Protected Budget
    protected_items = [i for i in orig_items if is_item_protected(i)]
    D_min_protected = sum(to_decimal(i.allocated_amount) for i in protected_items)

    # Strict Feasibility Validation
    if D_revised < D_min_protected:
        protected_names = [f"'{i.category}' ({format_inr(i.allocated_amount)})" for i in protected_items]
        reason = (
            f"The requested revised budget of {format_inr(D_revised)} is lower than the minimum protected budget of "
            f"{format_inr(D_min_protected)} required for your {len(protected_items)} protected categories: "
            f"{', '.join(protected_names)}. Protected categories cannot be reduced without explicit user authorization. "
            f"Please either unprotect categories or specify a budget target of at least {format_inr(D_min_protected)}."
        )
        return [], False, reason

    # 2. Allocate Contingency
    contingency_item = next((i for i in orig_items if i.is_contingency), None)
    allocated_decimals: Dict[str, Decimal] = {}

    if contingency_item:
        if is_item_protected(contingency_item):
            allocated_decimals[contingency_item.id] = to_decimal(contingency_item.allocated_amount)
        else:
            D_cont_amt = (D_revised * (to_decimal(contingency_pct) / PERCENT)).quantize(CENT, rounding=ROUND_HALF_UP)
            allocated_decimals[contingency_item.id] = D_cont_amt

    # 3. Allocate Protected Categories at 100% of current allocation
    for it in protected_items:
        if contingency_item and it.id == contingency_item.id:
            continue
        allocated_decimals[it.id] = to_decimal(it.allocated_amount)

    # 4. Remaining Pool for Flexible Categories
    D_allocated_so_far = sum(allocated_decimals.values())
    D_pool = max(Decimal("0.00"), D_revised - D_allocated_so_far)

    flexible_items = [i for i in orig_items if i.id not in allocated_decimals]

    # Reallocation and Category Boost support
    realloc_bonus: Dict[str, Decimal] = {}
    if reallocate_from and reallocate_to and flexible_items:
        rf_l = reallocate_from.lower()
        rt_l = reallocate_to.lower()
        from_item = next((i for i in flexible_items if rf_l in i.category.lower()), None)
        to_item = next((i for i in flexible_items if rt_l in i.category.lower()), None)
        if from_item and to_item:
            realloc_cut = (to_decimal(from_item.allocated_amount) * Decimal("0.35")).quantize(CENT, rounding=ROUND_HALF_UP)
            realloc_bonus[from_item.id] = -realloc_cut
            realloc_bonus[to_item.id] = realloc_cut

    if category_boosts and flexible_items:
        for b_cat, b_amt in category_boosts.items():
            b_low = b_cat.lower()
            matched_it = next((i for i in flexible_items if b_low in i.category.lower() or i.category.lower() in b_low), None)
            if matched_it:
                D_boost = to_decimal(b_amt)
                realloc_bonus[matched_it.id] = realloc_bonus.get(matched_it.id, Decimal("0.00")) + D_boost

    # 5. Weight flexible items by classification and priorities
    flex_weights: Dict[str, float] = {}
    for it in flexible_items:
        cat_l = it.category.lower()
        cls_mult = {
            "essential": 1.5,
            "important": 1.0,
            "custom": 0.8,
            "optional": 0.6,
        }.get(it.classification or "important", 1.0)

        base_w = (float(it.weight) or float(it.percentage) or 1.0) * cls_mult

        # Blend with Gemini suggested weights if provided
        if suggested_weights and cat_l in suggested_weights:
            base_w = 0.5 * base_w + 0.5 * max(0.1, float(suggested_weights[cat_l]))

        # Category percentage reductions
        matched_red = None
        for red_cat, red_pct in category_percentage_reductions.items():
            if red_cat.lower() in cat_l or cat_l in red_cat.lower():
                matched_red = red_pct
                break

        if matched_red:
            base_w = max(0.1, base_w * (1.0 - matched_red / 100.0))
        elif any(p == cat_l or p in cat_l for p in prioritized_lower):
            base_w *= 1.30
        elif is_reduction and it.classification == "optional":
            base_w = max(0.1, base_w * 0.70)

        flex_weights[it.id] = base_w

    sum_flex_weights = sum(flex_weights.values()) if flex_weights else 1.0

    # Allocate pool
    for it in flexible_items:
        w = flex_weights[it.id]
        raw_amt = (Decimal(str(w)) / Decimal(str(sum_flex_weights))) * D_pool
        D_amt = raw_amt.quantize(CENT, rounding=ROUND_HALF_UP)
        if it.id in realloc_bonus:
            D_amt += realloc_bonus[it.id]

        is_permitted = any(p == it.category.lower() or p in it.category.lower() for p in prioritized_lower) or (reallocate_to and reallocate_to.lower() in it.category.lower())
        if is_reduction and not is_permitted:
            D_amt = min(D_amt, to_decimal(it.allocated_amount))

        allocated_decimals[it.id] = max(Decimal("0.00"), D_amt)

    # 6. Reconcile exact difference down to 0.01 with Decimal
    D_current_total = sum(allocated_decimals.values())
    D_diff = D_revised - D_current_total

    if D_diff > Decimal("0.00") and flexible_items:
        headroom_candidates = []
        for i in flexible_items:
            is_permitted = any(p == i.category.lower() or p in i.category.lower() for p in prioritized_lower) or (reallocate_to and reallocate_to.lower() in i.category.lower())
            max_allowed = to_decimal(i.allocated_amount) if (is_reduction and not is_permitted) else Decimal("999999999.00")
            hr = max_allowed - allocated_decimals[i.id]
            if hr > Decimal("0.01"):
                headroom_candidates.append((i.id, hr))

        if headroom_candidates:
            for item_id, hr in headroom_candidates:
                add_amt = min(D_diff, hr)
                allocated_decimals[item_id] += add_amt
                D_diff -= add_amt
                if D_diff <= Decimal("0.00"):
                    break

        if D_diff > Decimal("0.00"):
            target_id = max(flexible_items, key=lambda x: x.allocated_amount).id
            allocated_decimals[target_id] += D_diff

    elif D_diff < Decimal("0.00") and flexible_items:
        target_id = max(flexible_items, key=lambda x: allocated_decimals[x.id]).id
        allocated_decimals[target_id] = max(Decimal("0.00"), allocated_decimals[target_id] + D_diff)

    # 7. Percentage calculations in Decimal
    percentages: Dict[str, Decimal] = {}
    for item in orig_items:
        amt = allocated_decimals[item.id]
        if D_revised > Decimal("0.00"):
            pct = ((amt / D_revised) * PERCENT).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            pct = Decimal("0.00")
        percentages[item.id] = pct

    # Reconcile percentages to 100.00%
    pct_sum = sum(percentages.values())
    pct_diff = PERCENT - pct_sum
    if pct_diff != Decimal("0.00") and orig_items:
        largest_item = max(orig_items, key=lambda x: allocated_decimals[x.id])
        percentages[largest_item.id] += pct_diff

    # 8. Build final balanced output dictionaries
    balanced_items = []
    for item in orig_items:
        amt = allocated_decimals[item.id]
        pct = percentages[item.id]
        balanced_items.append({
            "id": item.id,
            "category": item.category,
            "allocated_amount": float(amt),
            "percentage": float(pct),
            "weight": float(it.weight if (it := next((i for i in flexible_items if i.id == item.id), None)) else pct),
            "actual_spent": item.actual_spent,
            "is_contingency": item.is_contingency,
            "is_mandatory": item.is_mandatory,
            "notes": item.notes or "",
            "canonical_category": item.canonical_category,
            "classification": item.classification,
            "is_protected": is_item_protected(item),
        })

    return balanced_items, True, None


def balance_budget_allocations(
    orig_items: List[BudgetItem],
    revised_total_budget: float,
    protected_categories: List[str],
    prioritized_categories: List[str],
    category_percentage_reductions: Dict[str, float],
    suggested_weights: Optional[Dict[str, float]] = None,
    reallocate_from: Optional[str] = None,
    reallocate_to: Optional[str] = None,
    contingency_pct: float = 8.0,
    category_boosts: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Backward compatible wrapper around balance_budget_allocations_decimal."""
    items, is_feas, _ = balance_budget_allocations_decimal(
        orig_items=orig_items,
        revised_total_budget=revised_total_budget,
        protected_categories=protected_categories,
        prioritized_categories=prioritized_categories,
        category_percentage_reductions=category_percentage_reductions,
        suggested_weights=suggested_weights,
        reallocate_from=reallocate_from,
        reallocate_to=reallocate_to,
        contingency_pct=contingency_pct,
        category_boosts=category_boosts,
    )
    return items


# =====================================================================
# BUDGET ANALYSIS OVERVIEW & CATEGORY TAXONOMY
# =====================================================================

def analyze_budget(budget: BudgetSummary) -> BudgetAnalysis:
    """Analyzes existing budget allocations to surface actionable savings insights and taxonomy."""
    items = budget.items
    total_budget = budget.total_budget
    total_allocated = budget.total_allocated
    total_spent = budget.total_actual_spent

    remaining_budget = round(max(0.0, total_budget - total_spent), 2)

    non_contingency = [i for i in items if not i.is_contingency]
    candidate_items = non_contingency if non_contingency else items

    highest_item = max(candidate_items, key=lambda x: x.allocated_amount) if candidate_items else None
    highest_cat = highest_item.category if highest_item else "General"
    highest_amt = highest_item.allocated_amount if highest_item else 0.0
    highest_pct = highest_item.percentage if highest_item else 0.0

    potential_savings = []
    for item in non_contingency:
        cat_lower = item.category.lower()
        if item.classification == "optional":
            potential_savings.append(item.category)
        elif any(w in cat_lower for w in ["decor", "floral", "entertainment", "music", "attire", "invitation", "gift", "favor", "balloon"]):
            potential_savings.append(item.category)
        elif item.percentage >= 15.0 and "venue" not in cat_lower and "catering" not in cat_lower:
            potential_savings.append(item.category)

    if not potential_savings and non_contingency:
        sorted_by_size = sorted(non_contingency, key=lambda x: x.allocated_amount, reverse=True)
        potential_savings = [i.category for i in sorted_by_size[1:3]]

    distribution = [
        {
            "category": i.category,
            "allocated_amount": i.allocated_amount,
            "percentage": i.percentage,
            "actual_spent": i.actual_spent,
            "is_contingency": i.is_contingency,
            "classification": i.classification or "important",
            "is_protected": i.is_protected or i.is_contingency,
            "canonical_category": i.canonical_category,
        }
        for i in items
    ]

    warnings, suggestions = detect_duplicate_and_overlapping_categories(items, budget.currency)

    # Minimum protected budget calculation
    min_protected = sum(to_decimal(i.allocated_amount) for i in items if i.is_protected or i.is_contingency)
    protected_count = len([i for i in items if i.is_protected or i.is_contingency])

    return BudgetAnalysis(
        total_budget=total_budget,
        total_allocated=total_allocated,
        remaining_budget=remaining_budget,
        total_actual_spent=total_spent,
        highest_expense_category=highest_cat,
        highest_expense_amount=highest_amt,
        highest_expense_percentage=highest_pct,
        potential_savings_categories=potential_savings,
        category_distribution=distribution,
        duplicate_warnings=warnings,
        merge_suggestions=suggestions,
        standard_taxonomy=STANDARD_CATEGORIES,
        minimum_protected_budget=float(min_protected),
        protected_categories_count=protected_count,
    )


# =====================================================================
# MAIN OPTIMIZER SERVICE
# =====================================================================

class SmartBudgetOptimizer:
    def __init__(self):
        self.gemini = GeminiClient()

    def optimize(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        user_protected_categories: Optional[List[str]] = None,
    ) -> BudgetOptimizationResponse:
        sanitized_prompt = sanitize_user_input(user_prompt)
        orig_budget = plan.budget.total_budget
        plan_cat_names = [i.category for i in plan.budget.items]

        # STEP 1: Deterministic Intent and Specification Extraction
        spec = extract_budget_intent(
            sanitized_prompt,
            orig_budget,
            plan_cat_names,
        )

        # Merge any user_protected_categories passed via API or existing item protection
        all_protected_names = set(spec.protected_categories)
        if user_protected_categories:
            all_protected_names.update(user_protected_categories)
        for it in plan.budget.items:
            if it.is_protected:
                all_protected_names.add(it.category)
        spec.protected_categories = list(all_protected_names)

        # Infeasible request handling from prompt extraction
        if not spec.is_feasible:
            return self._build_infeasible_response(
                plan=plan,
                user_prompt=user_prompt,
                reason=spec.infeasibility_reason or "The requested budget optimization is infeasible.",
            )

        # Calculate expected revised budget
        if spec.target_revised_budget is not None:
            expected_revised_budget = spec.target_revised_budget
        elif spec.target_savings_amount is not None:
            expected_revised_budget = round(orig_budget - spec.target_savings_amount, 2)
        elif spec.target_savings_percentage is not None:
            expected_revised_budget = round(orig_budget * (1.0 - spec.target_savings_percentage / 100.0), 2)
        elif spec.category_percentage_reductions:
            cat_red_sum = 0.0
            for cat_name, red_pct in spec.category_percentage_reductions.items():
                for i in plan.budget.items:
                    if cat_name.lower() in i.category.lower():
                        cat_red_sum += round(i.allocated_amount * (red_pct / 100.0), 2)
            expected_revised_budget = round(orig_budget - cat_red_sum, 2)
        elif any(k in sanitized_prompt.lower() for k in ["save", "reduce", "cut", "lower", "cheaper", "affordable"]):
            calc_savings = round(orig_budget * 0.10, 2)
            expected_revised_budget = round(orig_budget - calc_savings, 2)
        else:
            expected_revised_budget = orig_budget

        # STEP 2: Strict Pre-Optimization Feasibility Check using Decimal
        D_expected_revised = to_decimal(expected_revised_budget)
        protected_spec_lower = [p.lower().strip() for p in spec.protected_categories]

        def is_item_protected_spec(it: BudgetItem) -> bool:
            if it.is_contingency:
                c_low = it.category.lower().strip()
                return any(p in c_low or c_low in p for p in protected_spec_lower)
            if it.is_protected:
                return True
            c_low = it.category.lower().strip()
            canon_low = (it.canonical_category or "").lower().strip()
            return any(p == c_low or p in c_low or (canon_low and (p == canon_low or p in canon_low)) for p in protected_spec_lower)

        protected_items = [i for i in plan.budget.items if is_item_protected_spec(i)]
        D_min_protected = sum(to_decimal(i.allocated_amount) for i in protected_items)

        if D_expected_revised < D_min_protected:
            protected_names = [f"'{i.category}' ({format_inr(i.allocated_amount)})" for i in protected_items]
            reason = (
                f"The requested revised budget of {format_inr(D_expected_revised)} is lower than the minimum protected budget of "
                f"{format_inr(D_min_protected)} required for your {len(protected_items)} protected categories: "
                f"{', '.join(protected_names)}. Protected categories cannot be reduced without explicit user authorization. "
                f"Please either unprotect categories or specify a budget target of at least {format_inr(D_min_protected)}."
            )
            return self._build_infeasible_response(
                plan=plan,
                user_prompt=user_prompt,
                reason=reason,
                minimum_protected_budget=float(D_min_protected),
                protected_categories=[i.category for i in protected_items],
            )

        # STEP 3: Generate Recommendations via Gemini AI or Fallback Engine
        if self.gemini.is_available():
            try:
                return self._optimize_with_gemini(
                    plan=plan,
                    user_prompt=sanitized_prompt,
                    spec=spec,
                    expected_revised_budget=expected_revised_budget,
                    minimum_protected_budget=float(D_min_protected),
                )
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Gemini budget optimization failed ({err_str}). Falling back to deterministic mathematical engine.")
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    note = "Gemini AI quota is currently exhausted (HTTP 429). Deterministic financial optimization applied."
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    note = "Gemini AI service is temporarily unavailable (HTTP 503). Deterministic financial optimization applied."
                elif "timeout" in err_str.lower():
                    note = "Gemini AI request timed out. Deterministic financial optimization applied."
                else:
                    note = f"Gemini AI recommendations unavailable ({type(e).__name__}). Deterministic financial optimization applied."
                
                return self._optimize_with_fallback(
                    plan=plan,
                    user_prompt=sanitized_prompt,
                    spec=spec,
                    expected_revised_budget=expected_revised_budget,
                    minimum_protected_budget=float(D_min_protected),
                    ai_error_note=note,
                )

        # Fallback to deterministic rule engine when Gemini is unavailable
        return self._optimize_with_fallback(
            plan=plan,
            user_prompt=sanitized_prompt,
            spec=spec,
            expected_revised_budget=expected_revised_budget,
            minimum_protected_budget=float(D_min_protected),
            ai_error_note="Gemini AI is not configured. Deterministic financial optimization applied.",
        )

    def _optimize_with_gemini(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        spec: BudgetOptimizationSpec,
        expected_revised_budget: float,
        minimum_protected_budget: float,
    ) -> BudgetOptimizationResponse:
        from google.genai import types

        orig_budget = plan.budget.total_budget
        expected_savings = round(orig_budget - expected_revised_budget, 2)

        categories_summary = [
            {
                "category": i.category,
                "canonical_category": i.canonical_category or map_category_to_canonical(i.category)[0],
                "allocated": i.allocated_amount,
                "percentage": i.percentage,
                "classification": i.classification or "important",
                "is_protected": i.is_protected or i.is_contingency or (i.category in spec.protected_categories),
                "is_contingency": i.is_contingency,
            }
            for i in plan.budget.items
        ]

        system_instruction = f"""You are an elite Celebration & Event Financial Optimization Advisor.
Analyze the current budget allocation, category classifications, and host objectives.
Return a structured JSON object recommending category-wise adjustments and detailed savings explanations.

CRITICAL FINANCIAL & PROTECTION RULES:
1. Target revised total budget: {expected_revised_budget} {plan.budget.currency}.
2. Original event budget: {orig_budget} {plan.budget.currency}.
3. Expected total savings: {expected_savings} {plan.budget.currency}.
4. LOCKED / PROTECTED CATEGORIES: {json.dumps(spec.protected_categories)}.
   - You MUST NOT reduce any protected category allocations.
   - Explain why these expenses are safeguarded.
5. Prioritized categories: {json.dumps(spec.prioritized_categories)}.
6. Essential categories (Venue, Food & Water, Contingency) take priority over Optional categories.
7. Return strictly valid JSON adhering to this schema:
{{
  "category_recommendations": [
    {{"category": "Venue & Lodging", "weight": 25.0, "reason": "Safeguarded core booking quality without location compromises."}},
    {{"category": "Catering & Bar", "weight": 25.0, "reason": "Maintained food quality per host requirement."}},
    {{"category": "Contingency", "weight": 8.0, "reason": "Preserved emergency buffer for unforeseen expenses."}}
  ],
  "where_money_saved": ["Reduced imported floral decor in favor of seasonal greenery", "..."],
  "why_recommended": "Balanced allocations to achieve target savings while safeguarding essential guest experiences.",
  "expenses_preserved": ["Catering & Bar preserved at highest possible quality per host requirement", "..."]
}}
"""

        prompt_content = f"""
Event: {plan.intake.title} ({plan.intake.event_type.title()} in {plan.intake.city})
Guests: {plan.intake.guest_count}
Current Total Budget: {plan.budget.total_budget} {plan.budget.currency}
Minimum Protected Budget: {minimum_protected_budget} {plan.budget.currency}
Current Allocations with Classifications: {json.dumps(categories_summary, indent=2)}

User Optimization Request:
"{user_prompt}"
"""

        response = self.gemini.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[system_instruction, prompt_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(json)?\n", "", raw_text)
            raw_text = re.sub(r"\n```$", "", raw_text)

        parsed = json.loads(raw_text)

        # STEP 4: Deterministic Numerical Calculations with Python Decimal
        # Never allow Gemini to independently determine final financial allocations!
        revised_budget = expected_revised_budget

        recs = parsed.get("category_recommendations", [])
        gemini_weights = {}
        notes_by_cat = {}
        for r in recs:
            cat_name = r.get("category", "")
            if cat_name:
                cat_l = cat_name.lower()
                gemini_weights[cat_l] = float(r.get("weight", 1.0))
                notes_by_cat[cat_l] = r.get("reason", "")

        balanced_raw, is_feas, infeas_reason = balance_budget_allocations_decimal(
            orig_items=plan.budget.items,
            revised_total_budget=revised_budget,
            protected_categories=spec.protected_categories,
            prioritized_categories=spec.prioritized_categories,
            category_percentage_reductions=spec.category_percentage_reductions,
            suggested_weights=gemini_weights,
            reallocate_from=spec.reallocate_from,
            reallocate_to=spec.reallocate_to,
            category_boosts=spec.category_boosts,
        )

        if not is_feas:
            return self._build_infeasible_response(
                plan=plan,
                user_prompt=user_prompt,
                reason=infeas_reason or "The requested optimization violates protected category constraints.",
                minimum_protected_budget=minimum_protected_budget,
                protected_categories=spec.protected_categories,
            )

        # Build final validated BudgetSummary
        final_items = [
            BudgetItem(
                id=b["id"] or f"cat_{idx}",
                category=b["category"],
                weight=b["weight"],
                percentage=b["percentage"],
                allocated_amount=b["allocated_amount"],
                actual_spent=b["actual_spent"],
                is_contingency=b["is_contingency"],
                is_mandatory=b["is_mandatory"],
                notes=notes_by_cat.get(b["category"].lower(), b["notes"] or "Adjusted allocation."),
                canonical_category=b.get("canonical_category"),
                classification=b.get("classification") or ("essential" if b["is_contingency"] else "important"),
                is_protected=b.get("is_protected", False),
            )
            for idx, b in enumerate(balanced_raw)
        ]

        optimized_summary = BudgetSummary(
            total_budget=revised_budget,
            total_allocated=round(sum(i.allocated_amount for i in final_items), 2),
            total_actual_spent=round(sum(i.actual_spent for i in final_items), 2),
            currency=plan.budget.currency,
            items=final_items,
            contingency_percentage=round(next((i.percentage for i in final_items if i.is_contingency), 8.0), 2),
            is_valid=True,
            validation_errors=[],
        )

        warnings, _ = detect_duplicate_and_overlapping_categories(plan.budget.items, plan.budget.currency)

        return self._build_response(
            plan=plan,
            user_prompt=user_prompt,
            engine_used="gemini",
            revised_budget=revised_budget,
            optimized_summary=optimized_summary,
            where_saved=parsed.get("where_money_saved", []),
            why_recommended=parsed.get("why_recommended", "AI optimized allocation based on host goals."),
            expenses_preserved=parsed.get("expenses_preserved", []),
            notes_by_cat=notes_by_cat,
            minimum_protected_budget=minimum_protected_budget,
            protected_categories=spec.protected_categories,
            duplicate_warnings=warnings,
        )

    def _optimize_with_fallback(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        spec: BudgetOptimizationSpec,
        expected_revised_budget: float,
        minimum_protected_budget: float,
        ai_error_note: Optional[str] = None,
    ) -> BudgetOptimizationResponse:
        """
        Deterministic Rule Engine when Gemini AI is not configured.
        Uses exact Python Decimal financial calculations.
        """
        orig_budget = plan.budget.total_budget
        revised_budget = expected_revised_budget

        balanced_raw, is_feas, infeas_reason = balance_budget_allocations_decimal(
            orig_items=plan.budget.items,
            revised_total_budget=revised_budget,
            protected_categories=spec.protected_categories,
            prioritized_categories=spec.prioritized_categories,
            category_percentage_reductions=spec.category_percentage_reductions,
            reallocate_from=spec.reallocate_from,
            reallocate_to=spec.reallocate_to,
            category_boosts=spec.category_boosts,
        )

        if not is_feas:
            return self._build_infeasible_response(
                plan=plan,
                user_prompt=user_prompt,
                reason=infeas_reason or "The requested optimization violates protected category constraints.",
                minimum_protected_budget=minimum_protected_budget,
                protected_categories=spec.protected_categories,
            )

        notes_by_cat = {}
        where_saved = []
        expenses_preserved = []

        for b in balanced_raw:
            cat_l = b["category"].lower()
            if b["is_contingency"]:
                notes_by_cat[cat_l] = "Emergency contingency buffer preserved."
                expenses_preserved.append("Emergency Contingency Reserve (~8%) maintained")
            elif b["is_protected"]:
                notes_by_cat[cat_l] = "Protected category allocation maintained at 100%."
                expenses_preserved.append(f"{b['category']} protected per host instruction")
            elif any(p in cat_l or cat_l in p for p in [c.lower() for c in spec.prioritized_categories]):
                notes_by_cat[cat_l] = "Prioritized category allocation maintained."
            else:
                orig_item = next((i for i in plan.budget.items if i.category.lower() == cat_l), None)
                if orig_item and b["allocated_amount"] < orig_item.allocated_amount:
                    notes_by_cat[cat_l] = "Streamlined non-critical elements and vendor packages."
                    where_saved.append(f"Optimized packages and non-essential rentals in {b['category']}")
                else:
                    notes_by_cat[cat_l] = "Standard allocation maintained."

        if not expenses_preserved:
            expenses_preserved.append("Core celebration essentials and contingency reserve")

        if not where_saved:
            calc_savings = round(orig_budget - revised_budget, 2)
            if calc_savings > 0:
                where_saved.append(f"Proportionately adjusted non-critical allocations to save {format_inr(calc_savings)}")
            else:
                where_saved.append("Balanced allocations across categories while preserving total budget ceiling.")

        if ai_error_note:
            why_rec = f"{ai_error_note} Optimized budget allocations mathematically to fulfill '{user_prompt}' while preserving key categories."
        else:
            why_rec = (
                f"Optimized budget allocations to fulfill: '{user_prompt}'. "
                f"Preserved primary experiential elements while trimming decorative rentals and secondary logistical costs."
            )

        final_items = [
            BudgetItem(
                id=b["id"] or f"cat_{idx}",
                category=b["category"],
                weight=b["weight"],
                percentage=b["percentage"],
                allocated_amount=b["allocated_amount"],
                actual_spent=b["actual_spent"],
                is_contingency=b["is_contingency"],
                is_mandatory=b["is_mandatory"],
                notes=notes_by_cat.get(b["category"].lower(), "Adjusted allocation."),
                canonical_category=b.get("canonical_category"),
                classification=b.get("classification") or ("essential" if b["is_contingency"] else "important"),
                is_protected=b.get("is_protected", False),
            )
            for idx, b in enumerate(balanced_raw)
        ]

        optimized_summary = BudgetSummary(
            total_budget=revised_budget,
            total_allocated=round(sum(i.allocated_amount for i in final_items), 2),
            total_actual_spent=round(sum(i.actual_spent for i in final_items), 2),
            currency=plan.budget.currency,
            items=final_items,
            contingency_percentage=round(next((i.percentage for i in final_items if i.is_contingency), 8.0), 2),
            is_valid=True,
            validation_errors=[],
        )

        warnings, _ = detect_duplicate_and_overlapping_categories(plan.budget.items, plan.budget.currency)

        engine_name = "deterministic_fallback" if ai_error_note else "fallback_rule_engine"

        return self._build_response(
            plan=plan,
            user_prompt=user_prompt,
            engine_used=engine_name,
            revised_budget=revised_budget,
            optimized_summary=optimized_summary,
            where_saved=where_saved,
            why_recommended=why_rec,
            expenses_preserved=expenses_preserved,
            notes_by_cat=notes_by_cat,
            minimum_protected_budget=minimum_protected_budget,
            protected_categories=spec.protected_categories,
            duplicate_warnings=warnings,
        )

    def _build_response(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        engine_used: str,
        revised_budget: float,
        optimized_summary: BudgetSummary,
        where_saved: List[str],
        why_recommended: str,
        expenses_preserved: List[str],
        notes_by_cat: Dict[str, str],
        minimum_protected_budget: float = 0.0,
        protected_categories: Optional[List[str]] = None,
        duplicate_warnings: Optional[List[DuplicateCategoryWarning]] = None,
    ) -> BudgetOptimizationResponse:
        orig_items_by_cat = {i.category.lower(): i for i in plan.budget.items}
        categories: List[CategoryOptimization] = []

        for new_item in optimized_summary.items:
            cat_l = new_item.category.lower()
            orig = orig_items_by_cat.get(cat_l)
            orig_amt = orig.allocated_amount if orig else 0.0
            orig_pct = orig.percentage if orig else 0.0

            rec_amt = new_item.allocated_amount
            rec_pct = new_item.percentage

            savings = round(orig_amt - rec_amt, 2)
            pct_change = round(((rec_amt - orig_amt) / orig_amt * 100), 1) if orig_amt > 0 else 0.0
            note = notes_by_cat.get(cat_l, new_item.notes or "Adjusted allocation.")

            categories.append(
                CategoryOptimization(
                    category=new_item.category,
                    original_amount=orig_amt,
                    original_percentage=orig_pct,
                    recommended_amount=rec_amt,
                    recommended_percentage=rec_pct,
                    savings=savings,
                    percentage_change=pct_change,
                    notes=note,
                    classification=new_item.classification,
                    is_protected=new_item.is_protected,
                    canonical_category=new_item.canonical_category,
                )
            )

        total_savings = round(max(0.0, plan.budget.total_budget - revised_budget), 2)
        savings_percentage = round((total_savings / plan.budget.total_budget * 100), 2) if plan.budget.total_budget > 0 else 0.0

        if total_savings > 0.0:
            saved_summary = (
                f"Total savings of {format_inr(total_savings)} "
                f"({savings_percentage:.1f}% reduction) from original budget of {format_inr(plan.budget.total_budget)} "
                f"to revised budget of {format_inr(revised_budget)}."
            )
        elif revised_budget == plan.budget.total_budget:
            positive_savings = sum(c.savings for c in categories if c.savings > 0)
            if positive_savings > 0:
                saved_summary = f"{format_inr(positive_savings)} reallocated across categories without changing total budget."
            else:
                saved_summary = "Budget allocations balanced while maintaining the current total budget."
        else:
            saved_summary = f"Total budget adjusted to {format_inr(revised_budget)}."

        explanation = OptimizationExplanation(
            where_money_saved=where_saved if isinstance(where_saved, list) else [str(where_saved)],
            why_recommended=why_recommended,
            expenses_preserved=expenses_preserved if isinstance(expenses_preserved, list) else [str(expenses_preserved)],
            total_saved_summary=saved_summary,
        )

        return BudgetOptimizationResponse(
            event_id=plan.event_id,
            user_prompt=user_prompt,
            engine_used=engine_used,
            original_total_budget=plan.budget.total_budget,
            revised_total_budget=revised_budget,
            total_savings=total_savings,
            savings_percentage=savings_percentage,
            is_feasible=True,
            is_valid=True,
            validation_errors=[],
            currency=plan.budget.currency,
            categories=categories,
            explanation=explanation,
            optimized_budget_summary=optimized_summary,
            minimum_protected_budget=minimum_protected_budget,
            protected_categories=protected_categories or [],
            duplicate_warnings=duplicate_warnings or [],
        )

    def _build_infeasible_response(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        reason: str,
        minimum_protected_budget: float = 0.0,
        protected_categories: Optional[List[str]] = None,
    ) -> BudgetOptimizationResponse:
        """
        Builds a safe, non-mutating response explaining why the request is infeasible.
        Enforces is_feasible = False and is_valid = False.
        """
        orig_budget = plan.budget.total_budget
        categories = [
            CategoryOptimization(
                category=i.category,
                original_amount=i.allocated_amount,
                original_percentage=i.percentage,
                recommended_amount=i.allocated_amount,
                recommended_percentage=i.percentage,
                savings=0.0,
                percentage_change=0.0,
                notes="Preserved original allocation without change.",
                classification=i.classification,
                is_protected=i.is_protected or i.is_contingency,
                canonical_category=i.canonical_category,
            )
            for i in plan.budget.items
        ]

        explanation = OptimizationExplanation(
            where_money_saved=[
                f"No reductions applied: {reason}"
            ],
            why_recommended=reason,
            expenses_preserved=["All category allocations preserved at current levels."],
            total_saved_summary=reason,
        )

        warnings, _ = detect_duplicate_and_overlapping_categories(plan.budget.items, plan.budget.currency)

        return BudgetOptimizationResponse(
            event_id=plan.event_id,
            user_prompt=user_prompt,
            engine_used="deterministic_validation",
            original_total_budget=orig_budget,
            revised_total_budget=orig_budget,
            total_savings=0.0,
            savings_percentage=0.0,
            is_feasible=False,
            is_valid=False,
            validation_errors=[reason],
            currency=plan.budget.currency,
            categories=categories,
            explanation=explanation,
            optimized_budget_summary=plan.budget,
            minimum_protected_budget=minimum_protected_budget,
            protected_categories=protected_categories or [],
            duplicate_warnings=warnings,
        )

    def _build_gemini_error_response(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        error_message: str,
    ) -> BudgetOptimizationResponse:
        """
        Builds a clear error response when Gemini AI fails.
        Never silently replaces failed AI responses with fabricated recommendations.
        """
        orig_budget = plan.budget.total_budget
        categories = [
            CategoryOptimization(
                category=i.category,
                original_amount=i.allocated_amount,
                original_percentage=i.percentage,
                recommended_amount=i.allocated_amount,
                recommended_percentage=i.percentage,
                savings=0.0,
                percentage_change=0.0,
                notes="Optimization failed due to AI service error.",
                classification=i.classification,
                is_protected=i.is_protected,
                canonical_category=i.canonical_category,
            )
            for i in plan.budget.items
        ]

        explanation = OptimizationExplanation(
            where_money_saved=[],
            why_recommended=error_message,
            expenses_preserved=["All existing budget allocations maintained without modification."],
            total_saved_summary="No optimizations applied due to AI service error.",
        )

        return BudgetOptimizationResponse(
            event_id=plan.event_id,
            user_prompt=user_prompt,
            engine_used="error",
            original_total_budget=orig_budget,
            revised_total_budget=orig_budget,
            total_savings=0.0,
            savings_percentage=0.0,
            is_feasible=False,
            is_valid=False,
            validation_errors=[error_message],
            currency=plan.budget.currency,
            categories=categories,
            explanation=explanation,
            optimized_budget_summary=plan.budget,
            minimum_protected_budget=0.0,
            protected_categories=[],
            duplicate_warnings=[],
        )
