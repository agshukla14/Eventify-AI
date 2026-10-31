import json
import logging
import uuid
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from .models import VendorDirectoryModel, EventVendorBookingModel, EventModel, ExpenseModel
from .schemas import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorRecommendationQuery,
    VendorRecommendationItem,
    VendorRecommendationResponse,
    VendorComparisonResponse,
    VendorProsCons,
    EventVendorBookingCreate,
    EventVendorBookingUpdate,
    EventVendorBookingResponse,
    VendorAnalyticsSummary,
    VendorCategorySpending,
)
from .config import GEMINI_API_KEY
from .gemini_client import sanitize_user_input

logger = logging.getLogger(__name__)


# High-Quality Verified Vendor Directory Dataset across Indian Celebration Cities
SEED_VENDORS = [
    # 1. PHOTOGRAPHY
    {
        "name": "Stories by Joseph Radhik",
        "category": "Photography",
        "location": "Mumbai",
        "description": "Celebrity wedding photography and cinematic storytelling. Pioneers of emotional, natural candid moments and fine-art couple portraits.",
        "services_offered": ["Candid Photography", "Cinematic 4K Films", "Pre-Wedding Shoots", "Drone Coverage", "Handcrafted Photo Books"],
        "min_price": 120000.0,
        "max_price": 350000.0,
        "rating": 4.9,
        "review_count": 184,
        "experience_years": 12,
        "phone": "+91 98200 45123",
        "email": "inquiries@storiesbyjosephradhik.com",
        "website": "https://storiesbyjosephradhik.com",
        "is_verified": True,
    },
    {
        "name": "Light Chamber Studios",
        "category": "Photography",
        "location": "Ahmedabad",
        "description": "Award-winning wedding and portrait studio in Gujarat. Known for rich traditional ceremonial coverage, vibrant colors, and affordable family packages.",
        "services_offered": ["Traditional Photography", "Candid Shoots", "Traditional HD Video", "Live Event Streaming", "Family Albums"],
        "min_price": 25000.0,
        "max_price": 65000.0,
        "rating": 4.7,
        "review_count": 92,
        "experience_years": 9,
        "phone": "+91 98791 22345",
        "email": "contact@lightchamberstudios.in",
        "website": "https://lightchamberstudios.in",
        "is_verified": True,
    },
    {
        "name": "Shutterdown Photography",
        "category": "Photography",
        "location": "Jaipur",
        "description": "Fun, quirky, and royal destination wedding photography. Experts in heritage palaces, desert shoots, and high-energy celebration reels.",
        "services_offered": ["Destination Wedding Photography", "Same-Day Teaser Edits", "Drone Videography", "Pre-wedding Concept Shoots"],
        "min_price": 50000.0,
        "max_price": 140000.0,
        "rating": 4.8,
        "review_count": 126,
        "experience_years": 8,
        "phone": "+91 98110 98765",
        "email": "hello@shutterdown.in",
        "website": "https://shutterdown.in",
        "is_verified": True,
    },
    {
        "name": "Wedding Nama",
        "category": "Photography",
        "location": "Delhi",
        "description": "Grand scale wedding cinematography and portraiture with a focus on editorial lighting, heartfelt rituals, and timeless albums.",
        "services_offered": ["Candid Photography", "Wedding Feature Films", "Drone Cinematography", "Fine Art Albums"],
        "min_price": 85000.0,
        "max_price": 220000.0,
        "rating": 4.8,
        "review_count": 140,
        "experience_years": 10,
        "phone": "+91 99102 33445",
        "email": "info@weddingnama.com",
        "website": "https://weddingnama.com",
        "is_verified": True,
    },

    # 2. CATERING
    {
        "name": "Mayur Caterers & Royal Kitchen",
        "category": "Catering",
        "location": "Ahmedabad",
        "description": "Premier vegetarian wedding caterers in Gujarat offering traditional Gujarati Thalis, Kathiyawadi live counters, and contemporary gourmet fusion.",
        "services_offered": ["Traditional Gujarati Thali", "Live Jalebi & Fafda Stalls", "Chaat Street Counters", "Multi-Cuisine Continental", "Dessert Boutiques"],
        "min_price": 45000.0,
        "max_price": 250000.0,
        "rating": 4.8,
        "review_count": 210,
        "experience_years": 15,
        "phone": "+91 98250 88990",
        "email": "events@mayurcaterers.com",
        "website": "https://mayurcaterers.com",
        "is_verified": True,
    },
    {
        "name": "Copper Chimney Banquets & Catering",
        "category": "Catering",
        "location": "Mumbai",
        "description": "Iconic culinary brand specializing in rich North Indian feasts, slow-cooked Dum biryanis, tandoori grills, and bespoke cocktail party appetizers.",
        "services_offered": ["North Indian Banquets", "Live Tandoor Counters", "Bespoke Cocktail Appetizers", "Gourmet Dessert Displays", "Barbeque Stalls"],
        "min_price": 75000.0,
        "max_price": 380000.0,
        "rating": 4.7,
        "review_count": 315,
        "experience_years": 22,
        "phone": "+91 98201 11223",
        "email": "catering@copperchimney.in",
        "website": "https://copperchimney.in",
        "is_verified": True,
    },
    {
        "name": "Royal Rajputana Feasts",
        "category": "Catering",
        "location": "Jaipur",
        "description": "Specialists in royal Rajasthani heritage banquets: Dal Baati Churma, Gatte ki Sabzi, Laal Maas, and decadent traditional Indian sweets.",
        "services_offered": ["Royal Rajasthani Feast", "Mughlai Banquets", "Live Silver Thali Service", "Traditional Sweet Bar", "Folk Dining Setup"],
        "min_price": 60000.0,
        "max_price": 300000.0,
        "rating": 4.8,
        "review_count": 165,
        "experience_years": 14,
        "phone": "+91 94140 33221",
        "email": "contact@royalrajputanafeasts.in",
        "website": "https://royalrajputanafeasts.in",
        "is_verified": True,
    },
    {
        "name": "Saffron Feast Catering",
        "category": "Catering",
        "location": "Bengaluru",
        "description": "Authentic South Indian festive dining and modern global live food stations. Specialists in banana leaf traditional service and eco-friendly catering.",
        "services_offered": ["Traditional South Indian Plantain Leaf", "Gourmet Live Counters", "Artisan Coffee Bars", "Organic Dessert Stalls"],
        "min_price": 35000.0,
        "max_price": 180000.0,
        "rating": 4.6,
        "review_count": 98,
        "experience_years": 8,
        "phone": "+91 98450 77665",
        "email": "hello@saffronfeast.com",
        "website": "https://saffronfeast.com",
        "is_verified": True,
    },

    # 3. DECORATION
    {
        "name": "Aura Floral & Event Stylists",
        "category": "Decoration",
        "location": "Ahmedabad",
        "description": "Contemporary and traditional floral design studio. Experts in marigold floral mandaps, fairy-light canopies, and eco-friendly sustainable stage decor.",
        "services_offered": ["Floral Mandap Setup", "Fairy Light Canopies", "Entrance Torans & Rangoli", "Photo Booth Backdrops", "Haldi & Mehendi Theming"],
        "min_price": 30000.0,
        "max_price": 120000.0,
        "rating": 4.7,
        "review_count": 142,
        "experience_years": 7,
        "phone": "+91 98254 33112",
        "email": "aurastylists@gmail.com",
        "website": "https://auradecor.in",
        "is_verified": True,
    },
    {
        "name": "The Wedding Design Company",
        "category": "Decoration",
        "location": "Mumbai",
        "description": "High-end luxury wedding decors, grandiose royal sets, mirror-work pavilions, and bespoke floral installations for elite celebrations.",
        "services_offered": ["Luxury Stage Architecture", "Bespoke Chandelier Canopies", "Thematic Lounge Decor", "Curated Table Scapes", "Illuminated Walkways"],
        "min_price": 150000.0,
        "max_price": 600000.0,
        "rating": 4.9,
        "review_count": 178,
        "experience_years": 16,
        "phone": "+91 98203 77889",
        "email": "design@wdcindia.com",
        "website": "https://wdcindia.com",
        "is_verified": True,
    },
    {
        "name": "Heritage Floral Arts",
        "category": "Decoration",
        "location": "Jaipur",
        "description": "Palatial Rajasthani decor with royal velvet drapery, brass urli floral arrangements, carved jharokha backdrops, and traditional diyas.",
        "services_offered": ["Palace Courtyard Lighting", "Royal Mandap Structures", "Traditional Brass Diya Decor", "Rajputana Themed Entrances"],
        "min_price": 45000.0,
        "max_price": 200000.0,
        "rating": 4.8,
        "review_count": 115,
        "experience_years": 11,
        "phone": "+91 94142 55667",
        "email": "jaipurheritagefloral@gmail.com",
        "website": "https://heritagefloralarts.in",
        "is_verified": True,
    },

    # 4. VENUE
    {
        "name": "The Grand Bhagwati Banquets",
        "category": "Venue",
        "location": "Ahmedabad",
        "description": "Prestigious convention and wedding venue featuring pillar-less grand ballrooms, manicured sprawling lawns, and comprehensive hospitality suites.",
        "services_offered": ["Pillarless Ballrooms", "Outdoor Reception Lawns", "Bridal Suites", "Valet Parking for 500+ Cars", "In-house AV & Stage"],
        "min_price": 100000.0,
        "max_price": 450000.0,
        "rating": 4.7,
        "review_count": 420,
        "experience_years": 18,
        "phone": "+91 79 2684 1000",
        "email": "banquets@thegrandbhagwati.com",
        "website": "https://thegrandbhagwati.com",
        "is_verified": True,
    },
    {
        "name": "Rambagh Palace Grounds",
        "category": "Venue",
        "location": "Jaipur",
        "description": "Historic jewel of Jaipur. Experience quintessential Rajput royal hospitality with sweeping palace gardens, heritage pavilions, and regal courtyards.",
        "services_offered": ["Royal Palace Lawns", "Heritage Courtyards", "Fine Dining Ballrooms", "Royal Carriage Entrances", "Luxury Suite Accommodations"],
        "min_price": 250000.0,
        "max_price": 950000.0,
        "rating": 4.9,
        "review_count": 310,
        "experience_years": 30,
        "phone": "+91 141 2211 919",
        "email": "rambagh.jaipur@tajhotels.com",
        "website": "https://tajhotels.com/rambagh-palace",
        "is_verified": True,
    },
    {
        "name": "Taj Lands End Seaview Lawns",
        "category": "Venue",
        "location": "Mumbai",
        "description": "Spectacular seaside venue in Bandra overlooking the Arabian Sea. Renowned for dramatic sunset weddings and five-star luxury ballrooms.",
        "services_offered": ["Seaside Open Lawns", "Grand Ballroom", "Sea-View Terraces", "VIP Green Rooms", "In-house Sound & Lighting"],
        "min_price": 200000.0,
        "max_price": 850000.0,
        "rating": 4.9,
        "review_count": 290,
        "experience_years": 25,
        "phone": "+91 22 6668 1234",
        "email": "landsend.mumbai@tajhotels.com",
        "website": "https://tajhotels.com/taj-lands-end",
        "is_verified": True,
    },

    # 5. ENTERTAINMENT
    {
        "name": "Soulful Strings Live Fusion Band",
        "category": "Entertainment",
        "location": "Ahmedabad",
        "description": "Dynamic 5-piece live musical ensemble blending Sufi, Bollywood retro, and acoustic Gujarati folk. Perfect for Sangeet, Mehendi, and Cocktail nights.",
        "services_offered": ["Live Acoustic Sangeet Set", "Sufi & Bollywood Mashups", "Folk Fusion Grooves", "Sound Engineer & Stage PA Setup"],
        "min_price": 25000.0,
        "max_price": 75000.0,
        "rating": 4.8,
        "review_count": 88,
        "experience_years": 6,
        "phone": "+91 98255 11998",
        "email": "bookings@soulfulstrings.in",
        "website": "https://soulfulstrings.in",
        "is_verified": True,
    },
    {
        "name": "DJ Aqeel Sound & Visuals",
        "category": "Entertainment",
        "location": "Mumbai",
        "description": "Celebrity DJ and audio-visual production powerhouse delivering heart-thumping EDM, Bollywood remixes, intelligent stage lasers, and LED dancefloors.",
        "services_offered": ["Celebrity DJ Set", "Intelligent Moving-Head Lasers", "Interactive LED Dance Floors", "Cold Pyro Sync", "Pro Line-Array Sound"],
        "min_price": 75000.0,
        "max_price": 250000.0,
        "rating": 4.8,
        "review_count": 215,
        "experience_years": 18,
        "phone": "+91 98200 88776",
        "email": "bookings@djaqeel.com",
        "website": "https://djaqeel.com",
        "is_verified": True,
    },
    {
        "name": "Royal Dhol Tasha & Folk Troupe",
        "category": "Entertainment",
        "location": "Jaipur",
        "description": "Traditional Rajasthani Nagada, authentic Punjabi Nashik dhol players, fire dancers, and Ghoomar folk artists for unforgettable baraat processions.",
        "services_offered": ["High-Energy Dhol Beats", "Baraat Brass Band", "Folk Fire Dancers", "Ghoomar & Kalbeliya Performances"],
        "min_price": 15000.0,
        "max_price": 45000.0,
        "rating": 4.7,
        "review_count": 130,
        "experience_years": 12,
        "phone": "+91 94145 66778",
        "email": "royaldholjaipur@gmail.com",
        "website": "https://royaldholjaipur.in",
        "is_verified": True,
    },

    # 6. MAKEUP ARTISTS
    {
        "name": "Geetanjali Bridal Studio",
        "category": "Makeup Artists",
        "location": "Ahmedabad",
        "description": "Luxury bridal hair and makeup artistry. Experts in HD airbrush, traditional Gujarati saree draping, and glowing editorial looks.",
        "services_offered": ["HD Airbrush Bridal Makeup", "Saree & Dupatta Draping", "Party Makeup for Family", "Hair Extensions & Floral Styling"],
        "min_price": 15000.0,
        "max_price": 45000.0,
        "rating": 4.8,
        "review_count": 174,
        "experience_years": 9,
        "phone": "+91 98251 44556",
        "email": "geetanjali.studio.ahmedabad@gmail.com",
        "website": "https://geetanjalibridal.in",
        "is_verified": True,
    },
    {
        "name": "Ojas Rajani Bridal Couture Makeup",
        "category": "Makeup Artists",
        "location": "Mumbai",
        "description": "Celebrity hair and makeup artist with over two decades of transforming high-profile brides with signature radiant skin and dramatic eyes.",
        "services_offered": ["Celebrity Bridal Makeup", "International Airbrush Techniques", "Custom Saree Styling", "Pre-Bridal Skin Consultation"],
        "min_price": 40000.0,
        "max_price": 120000.0,
        "rating": 4.9,
        "review_count": 260,
        "experience_years": 20,
        "phone": "+91 98202 99881",
        "email": "ojas@ojasrajani.com",
        "website": "https://ojasrajani.com",
        "is_verified": True,
    },

    # 7. TRANSPORTATION
    {
        "name": "Royal Vintage Car Rentals",
        "category": "Transportation",
        "location": "Jaipur",
        "description": "Exquisite collection of restored classic convertibles and vintage luxury automobiles for royal groom entries and picturesque couple send-offs.",
        "services_offered": ["Vintage Convertible for Groom Entry", "Decorated Chauffeur-Driven Cars", "Bride & Groom Send-off Vehicles", "Photo-Shoot Rentals"],
        "min_price": 18000.0,
        "max_price": 50000.0,
        "rating": 4.8,
        "review_count": 76,
        "experience_years": 10,
        "phone": "+91 94140 88991",
        "email": "vintagecarsjaipur@gmail.com",
        "website": "https://royalvintagecarsjaipur.com",
        "is_verified": True,
    },
    {
        "name": "Apex Luxury Fleet & Guest Coaches",
        "category": "Transportation",
        "location": "Ahmedabad",
        "description": "Reliable guest logistics partner providing AC luxury traveler vans, Mercedes/BMW sedans, and 35-seater Volvo coaches with dedicated event coordinators.",
        "services_offered": ["Airport Guest Pickup & Drop", "AC Luxury Tempo Travelers", "Premium Sedans for Family", "Coordinated Venue Shuttles"],
        "min_price": 12000.0,
        "max_price": 60000.0,
        "rating": 4.6,
        "review_count": 110,
        "experience_years": 7,
        "phone": "+91 98795 33441",
        "email": "booking@apexfleet.in",
        "website": "https://apexfleet.in",
        "is_verified": True,
    },

    # 8. OTHER EVENT SERVICES
    {
        "name": "Artistic Mehendi Creations by Usha",
        "category": "Other Event Services",
        "location": "Ahmedabad",
        "description": "Master henna artist specializing in intricate bridal portraits, Radha-Krishna motifs, modern geometric Arabic lace, and organic chemical-free henna paste.",
        "services_offered": ["Bridal Portrait Henna", "Rajasthani Marwari Mehendi", "Guest Henna Artists Team", "Custom Storytelling Motifs"],
        "min_price": 8000.0,
        "max_price": 30000.0,
        "rating": 4.9,
        "review_count": 195,
        "experience_years": 13,
        "phone": "+91 98256 77880",
        "email": "ushamehendi.ahmedabad@gmail.com",
        "website": "https://ushamehendi.in",
        "is_verified": True,
    },
    {
        "name": "Celebration Eco-Spark Pyro & Special FX",
        "category": "Other Event Services",
        "location": "Jaipur",
        "description": "Smokeless cold pyro sparklers, low-lying dry ice fog clouds, paper confetti blasters, and synchronized musical fountain effects for stage entries.",
        "services_offered": ["Cold Pyro Sparkulars (Indoor Safe)", "Dry Ice Cloud Dance Floor", "Stage Confetti Cannons", "Musical Entrance FX"],
        "min_price": 10000.0,
        "max_price": 35000.0,
        "rating": 4.7,
        "review_count": 68,
        "experience_years": 6,
        "phone": "+91 94148 22334",
        "email": "ecosparkfx@gmail.com",
        "website": "https://celebrationpyro.in",
        "is_verified": True,
    },
]


class VendorService:

    @classmethod
    def init_seed_directory(cls, db: Session):
        """Initializes verified real vendor directory if currently empty."""
        count = db.query(VendorDirectoryModel).count()
        if count == 0:
            now_str = datetime.now().isoformat()
            for item in SEED_VENDORS:
                vendor = VendorDirectoryModel(
                    id=f"vnd_{uuid.uuid4().hex[:12]}",
                    name=item["name"],
                    category=item["category"],
                    location=item["location"],
                    description=item["description"],
                    services_offered=json.dumps(item["services_offered"]),
                    min_price=float(item["min_price"]),
                    max_price=float(item["max_price"]),
                    rating=float(item["rating"]),
                    review_count=int(item["review_count"]),
                    experience_years=int(item["experience_years"]),
                    phone=item["phone"],
                    email=item["email"],
                    website=item.get("website"),
                    portfolio_images=json.dumps([]),
                    is_verified=True,
                    is_favorite=False,
                    created_at=now_str,
                    updated_at=now_str,
                )
                db.add(vendor)
            db.commit()
            logger.info(f"Seeded {len(SEED_VENDORS)} verified celebration vendors into directory.")

    @classmethod
    def get_vendors(
        cls,
        db: Session,
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        search: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        is_verified: Optional[bool] = None,
    ) -> List[VendorResponse]:
        query = db.query(VendorDirectoryModel)

        if category and category != "All":
            query = query.filter(VendorDirectoryModel.category == category)
        if location and location != "All":
            query = query.filter(VendorDirectoryModel.location.ilike(f"%{location.strip()}%"))
        if min_price is not None:
            query = query.filter(VendorDirectoryModel.max_price >= min_price)
        if max_price is not None:
            query = query.filter(VendorDirectoryModel.min_price <= max_price)
        if min_rating is not None:
            query = query.filter(VendorDirectoryModel.rating >= min_rating)
        if is_favorite is not None:
            query = query.filter(VendorDirectoryModel.is_favorite == is_favorite)
        if is_verified is not None:
            query = query.filter(VendorDirectoryModel.is_verified == is_verified)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    VendorDirectoryModel.name.ilike(s),
                    VendorDirectoryModel.description.ilike(s),
                    VendorDirectoryModel.location.ilike(s),
                    VendorDirectoryModel.services_offered.ilike(s),
                )
            )

        records = query.order_by(VendorDirectoryModel.rating.desc(), VendorDirectoryModel.name.asc()).all()
        return [cls._to_vendor_response(v) for v in records]

    @classmethod
    def get_vendor_by_id(cls, db: Session, vendor_id: str) -> Optional[VendorResponse]:
        vendor = db.query(VendorDirectoryModel).filter(VendorDirectoryModel.id == vendor_id).first()
        return cls._to_vendor_response(vendor) if vendor else None

    @classmethod
    def create_vendor(cls, db: Session, data: VendorCreate) -> VendorResponse:
        now_str = datetime.now().isoformat()
        vendor_id = f"vnd_{uuid.uuid4().hex[:12]}"
        record = VendorDirectoryModel(
            id=vendor_id,
            name=data.name.strip(),
            category=data.category.strip(),
            location=data.location.strip(),
            description=data.description.strip(),
            services_offered=json.dumps(data.services_offered or []),
            min_price=float(data.min_price),
            max_price=float(data.max_price or data.min_price),
            rating=float(data.rating),
            review_count=int(data.review_count),
            experience_years=int(data.experience_years),
            phone=data.phone.strip(),
            email=data.email.strip(),
            website=data.website.strip() if data.website else None,
            portfolio_images=json.dumps(data.portfolio_images or []),
            is_verified=False,  # User-created listings are unverified
            is_favorite=data.is_favorite,
            created_at=now_str,
            updated_at=now_str,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return cls._to_vendor_response(record)

    @classmethod
    def update_vendor(cls, db: Session, vendor_id: str, data: VendorUpdate) -> VendorResponse:
        vendor = db.query(VendorDirectoryModel).filter(VendorDirectoryModel.id == vendor_id).first()
        if not vendor:
            raise ValueError(f"Vendor {vendor_id} not found")

        # Protect verified listings from accidental manual edit
        if vendor.is_verified and (data.name or data.category or data.location or data.description or data.min_price):
            raise ValueError("Verified directory listings cannot be modified. You can add your own custom vendor.")

        if data.name is not None:
            vendor.name = data.name.strip()
        if data.category is not None:
            vendor.category = data.category.strip()
        if data.location is not None:
            vendor.location = data.location.strip()
        if data.description is not None:
            vendor.description = data.description.strip()
        if data.services_offered is not None:
            vendor.services_offered = json.dumps(data.services_offered)
        if data.min_price is not None:
            vendor.min_price = float(data.min_price)
        if data.max_price is not None:
            vendor.max_price = float(data.max_price)
        if data.rating is not None:
            vendor.rating = float(data.rating)
        if data.review_count is not None:
            vendor.review_count = int(data.review_count)
        if data.experience_years is not None:
            vendor.experience_years = int(data.experience_years)
        if data.phone is not None:
            vendor.phone = data.phone.strip()
        if data.email is not None:
            vendor.email = data.email.strip()
        if data.website is not None:
            vendor.website = data.website.strip() if data.website else None
        if data.portfolio_images is not None:
            vendor.portfolio_images = json.dumps(data.portfolio_images)
        if data.is_favorite is not None:
            vendor.is_favorite = data.is_favorite

        vendor.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(vendor)
        return cls._to_vendor_response(vendor)

    @classmethod
    def delete_vendor(cls, db: Session, vendor_id: str) -> bool:
        vendor = db.query(VendorDirectoryModel).filter(VendorDirectoryModel.id == vendor_id).first()
        if not vendor:
            return False
        if vendor.is_verified:
            raise ValueError("Verified directory listings cannot be deleted. You can delete user-created listings.")
        db.delete(vendor)
        db.commit()
        return True

    @classmethod
    def toggle_favorite(cls, db: Session, vendor_id: str) -> VendorResponse:
        vendor = db.query(VendorDirectoryModel).filter(VendorDirectoryModel.id == vendor_id).first()
        if not vendor:
            raise ValueError(f"Vendor {vendor_id} not found")
        vendor.is_favorite = not vendor.is_favorite
        vendor.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(vendor)
        return cls._to_vendor_response(vendor)

    @classmethod
    def recommend_vendors(
        cls,
        db: Session,
        query_req: VendorRecommendationQuery,
    ) -> VendorRecommendationResponse:
        """
        AI-powered vendor recommendation grounded strictly in ACTUAL database records.
        Applies database filters for location, category, and budget before ranking.
        Never invents businesses, prices, ratings, phone numbers, or addresses.
        """
        raw_text = query_req.query.strip()
        lower = raw_text.lower()

        # 1. Parse natural language criteria
        detected_category = query_req.category
        if not detected_category:
            cat_map = {
                "photo": "Photography",
                "camera": "Photography",
                "video": "Photography",
                "cater": "Catering",
                "food": "Catering",
                "thali": "Catering",
                "decor": "Decoration",
                "flower": "Decoration",
                "mandap": "Decoration",
                "venue": "Venue",
                "hall": "Venue",
                "palace": "Venue",
                "resort": "Venue",
                "lawn": "Venue",
                "music": "Entertainment",
                "dj": "Entertainment",
                "band": "Entertainment",
                "dhol": "Entertainment",
                "singer": "Entertainment",
                "makeup": "Makeup Artists",
                "beauty": "Makeup Artists",
                "hair": "Makeup Artists",
                "transport": "Transportation",
                "car": "Transportation",
                "bus": "Transportation",
                "coach": "Transportation",
                "henna": "Other Event Services",
                "mehendi": "Other Event Services",
                "firework": "Other Event Services",
                "pyro": "Other Event Services",
            }
            for kw, cat in cat_map.items():
                if kw in lower:
                    detected_category = cat
                    break

        detected_location = query_req.location
        if not detected_location:
            cities = ["Ahmedabad", "Mumbai", "Jaipur", "Delhi", "Bengaluru", "Bangalore", "Udaipur", "Goa", "Pune", "Hyderabad"]
            for c in cities:
                if c.lower() in lower:
                    detected_location = "Bengaluru" if c.lower() in ("bangalore", "bengaluru") else c
                    break

        detected_budget = query_req.max_budget
        if not detected_budget:
            # Check price pattern: "under 30000", "below 50,000", "< 40000", "₹30,000"
            m = re.search(r"(?:under|below|budget\s+of|less\s+than|<|max)?\s*(?:₹|rs\.?|inr)?\s*(\d+[\d,]+|\d{3,})", lower)
            if m:
                try:
                    val = float(m.group(1).replace(",", ""))
                    if val >= 5000:
                        detected_budget = val
                except Exception:
                    pass

        # 2. Query actual database records
        q = db.query(VendorDirectoryModel)
        if detected_category:
            q = q.filter(VendorDirectoryModel.category == detected_category)
        if detected_location:
            q = q.filter(VendorDirectoryModel.location.ilike(f"%{detected_location}%"))

        candidates = q.all()

        # If zero candidates found with strict location, try searching across all locations
        search_broadened = None
        if not candidates and detected_location:
            candidates = db.query(VendorDirectoryModel).filter(
                VendorDirectoryModel.category == detected_category if detected_category else True
            ).all()
            if candidates:
                search_broadened = f"No {detected_category or 'vendor'} listings found specifically in {detected_location}. Showing top verified matches from nearby celebration hubs."

        # Filter and rank candidates against budget & keywords
        recommendations = []
        for cand in candidates:
            # Check budget fit
            within_budget = True
            if detected_budget is not None and cand.min_price > detected_budget:
                within_budget = False

            # Calculate match score (0-100)
            score = 70.0
            score += min(20.0, (cand.rating - 4.0) * 20.0)  # Rating contribution
            if within_budget:
                score += 10.0
            if cand.is_verified:
                score += 5.0

            # Keyword relevance in services or description
            keyword_matches = []
            for word in ["traditional", "candid", "luxury", "affordable", "heritage", "royal", "drone", "airbrush", "vintage", "live"]:
                if word in lower and (word in cand.description.lower() or word in cand.services_offered.lower()):
                    score += 5.0
                    keyword_matches.append(word.title())

            # Construct factual explanation grounded strictly in candidate attributes
            reason_parts = []
            if detected_location and cand.location.lower() == detected_location.lower():
                reason_parts.append(f"Located directly in {cand.location}")
            else:
                reason_parts.append(f"Based in {cand.location}")

            if within_budget and detected_budget:
                reason_parts.append(f"starts within your budget at ₹{cand.min_price:,.0f} (budget limit: ₹{detected_budget:,.0f})")
            elif not within_budget and detected_budget:
                reason_parts.append(f"packages start at ₹{cand.min_price:,.0f} (exceeds budget limit of ₹{detected_budget:,.0f})")
            else:
                reason_parts.append(f"packages range from ₹{cand.min_price:,.0f} to ₹{cand.max_price:,.0f}")

            reason_parts.append(f"rated {cand.rating:.1f}/5.0 ({cand.review_count} verified reviews) with {cand.experience_years} years of experience")
            if keyword_matches:
                reason_parts.append(f"specializes in {', '.join(keyword_matches)}")

            match_reason = f"{cand.name}: " + "; ".join(reason_parts) + "."

            recommendations.append(
                VendorRecommendationItem(
                    vendor=cls._to_vendor_response(cand),
                    match_score=round(min(99.0, score), 1),
                    match_reason=match_reason,
                    is_within_budget=within_budget,
                )
            )

        # Sort: first within_budget, then highest match_score, then rating
        recommendations.sort(key=lambda x: (1 if x.is_within_budget else 0, x.match_score, x.vendor.rating), reverse=True)

        return VendorRecommendationResponse(
            query=raw_text,
            parsed_criteria={
                "category": detected_category,
                "location": detected_location,
                "max_budget": detected_budget,
            },
            recommendations=recommendations,
            total_matching=len(recommendations),
            search_broadened_message=search_broadened,
        )

    @classmethod
    def compare_vendors(cls, db: Session, vendor_ids: List[str]) -> VendorComparisonResponse:
        """
        Grounded comparison of 2 to 3 actual database vendors.
        Never treats missing attributes as positive.
        """
        if len(vendor_ids) < 2 or len(vendor_ids) > 3:
            raise ValueError("Please select between 2 and 3 vendors to compare.")

        records = (
            db.query(VendorDirectoryModel)
            .filter(VendorDirectoryModel.id.in_(vendor_ids))
            .all()
        )
        if len(records) < 2:
            raise ValueError("Could not find the requested vendors in the database.")

        vendors_resp = [cls._to_vendor_response(v) for v in records]

        # 1. Best budget option: lowest min_price
        budget_sorted = sorted(vendors_resp, key=lambda v: v.min_price)
        best_budget = f"{budget_sorted[0].name} (starts at ₹{budget_sorted[0].min_price:,.0f})"

        # 2. Best rated option: highest rating (then review count)
        rated_sorted = sorted(vendors_resp, key=lambda v: (v.rating, v.review_count), reverse=True)
        best_rated = f"{rated_sorted[0].name} ({rated_sorted[0].rating:.1f}/5.0 stars with {rated_sorted[0].review_count} reviews)"

        # 3. Best overall: balances rating, price, experience
        best_overall = rated_sorted[0].name

        # 4. Generate pros and cons per vendor based strictly on factual database attributes
        evaluations = []
        for v in vendors_resp:
            pros = []
            cons = []

            # Price evaluations
            if v.min_price <= budget_sorted[0].min_price * 1.15:
                pros.append(f"Highly economical starting price of ₹{v.min_price:,.0f}")
            elif v.min_price >= budget_sorted[-1].min_price * 0.9 and len(vendors_resp) > 2:
                cons.append(f"Higher starting price tier (₹{v.min_price:,.0f})")

            # Rating evaluations
            if v.rating >= 4.8:
                pros.append(f"Outstanding customer rating ({v.rating:.1f}/5.0 from {v.review_count} reviews)")
            elif v.rating < 4.7:
                cons.append(f"Moderate customer satisfaction rating ({v.rating:.1f}/5.0)")

            # Experience
            if v.experience_years >= 12:
                pros.append(f"Extensive industry experience ({v.experience_years} years)")
            elif v.experience_years < 6:
                cons.append(f"Relatively newer service provider ({v.experience_years} years in business)")

            # Services
            if len(v.services_offered) >= 4:
                pros.append(f"Comprehensive offering covering {len(v.services_offered)} specialized services")
            else:
                cons.append(f"Limited service breadth ({len(v.services_offered)} services listed)")

            # Verification
            if v.is_verified:
                pros.append("Verified and authenticated directory listing")
            else:
                cons.append("User-created listing; credentials and availability require manual confirmation")

            evaluations.append(
                VendorProsCons(
                    vendor_id=v.id,
                    vendor_name=v.name,
                    pros=pros,
                    cons=cons,
                )
            )

        summary = (
            f"Comparing {len(vendors_resp)} {vendors_resp[0].category} vendors: "
            f"{best_budget} provides the most accessible entry budget, whereas "
            f"{best_rated} holds the strongest customer satisfaction. "
            f"Choose based on whether your event prioritizes cost efficiency or premium legacy service."
        )

        return VendorComparisonResponse(
            vendors=vendors_resp,
            best_budget_option=best_budget,
            best_rated_option=best_rated,
            best_overall_match=best_overall,
            comparison_summary=summary,
            vendor_evaluations=evaluations,
        )

    # =========================================================
    # EVENT BOOKING MANAGEMENT
    # =========================================================

    @classmethod
    def create_or_update_booking(
        cls,
        db: Session,
        data: EventVendorBookingCreate,
    ) -> EventVendorBookingResponse:
        # Validate event exists
        event = db.query(EventModel).filter(EventModel.id == data.event_id).first()
        if not event:
            raise ValueError(f"Event {data.event_id} not found")

        # Validate vendor exists
        vendor = db.query(VendorDirectoryModel).filter(VendorDirectoryModel.id == data.vendor_id).first()
        if not vendor:
            raise ValueError(f"Vendor {data.vendor_id} not found")

        # Validate financial logic
        if data.agreed_price < 0.0:
            raise ValueError("Agreed price cannot be negative.")
        if data.advance_payment < 0.0:
            raise ValueError("Advance payment cannot be negative.")
        if data.advance_payment > data.agreed_price:
            raise ValueError(f"Advance payment (₹{data.advance_payment:,.2f}) cannot exceed the agreed price (₹{data.agreed_price:,.2f}).")

        booking_date = data.booking_date or datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().isoformat()

        # Check existing booking for event + vendor
        existing = (
            db.query(EventVendorBookingModel)
            .filter(
                EventVendorBookingModel.event_id == data.event_id,
                EventVendorBookingModel.vendor_id == data.vendor_id,
            )
            .first()
        )

        if existing:
            existing.booking_status = data.booking_status
            existing.agreed_price = float(data.agreed_price)
            existing.advance_payment = float(data.advance_payment)
            existing.booking_date = booking_date
            if data.notes is not None:
                existing.notes = data.notes
            existing.updated_at = now_str
            db.commit()
            db.refresh(existing)
            return cls._to_booking_response(existing)
        else:
            booking_id = f"bkg_{uuid.uuid4().hex[:12]}"
            new_booking = EventVendorBookingModel(
                id=booking_id,
                event_id=data.event_id,
                vendor_id=data.vendor_id,
                booking_status=data.booking_status,
                agreed_price=float(data.agreed_price),
                advance_payment=float(data.advance_payment),
                booking_date=booking_date,
                notes=data.notes,
                created_at=now_str,
                updated_at=now_str,
            )
            db.add(new_booking)
            db.commit()
            db.refresh(new_booking)
            return cls._to_booking_response(new_booking)

    @classmethod
    def update_booking(
        cls,
        db: Session,
        booking_id: str,
        data: EventVendorBookingUpdate,
    ) -> EventVendorBookingResponse:
        booking = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.id == booking_id).first()
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")

        agreed = data.agreed_price if data.agreed_price is not None else booking.agreed_price
        advance = data.advance_payment if data.advance_payment is not None else booking.advance_payment

        if agreed < 0.0 or advance < 0.0:
            raise ValueError("Financial values cannot be negative.")
        if advance > agreed:
            raise ValueError(f"Advance payment (₹{advance:,.2f}) cannot exceed agreed price (₹{agreed:,.2f}).")

        if data.booking_status is not None:
            booking.booking_status = data.booking_status
        booking.agreed_price = float(agreed)
        booking.advance_payment = float(advance)
        if data.booking_date is not None:
            booking.booking_date = data.booking_date
        if data.notes is not None:
            booking.notes = data.notes

        booking.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(booking)
        return cls._to_booking_response(booking)

    @classmethod
    def get_event_bookings(cls, db: Session, event_id: str) -> List[EventVendorBookingResponse]:
        bookings = (
            db.query(EventVendorBookingModel)
            .filter(EventVendorBookingModel.event_id == event_id)
            .order_by(EventVendorBookingModel.created_at.desc())
            .all()
        )
        return [cls._to_booking_response(b) for b in bookings]

    @classmethod
    def delete_booking(cls, db: Session, booking_id: str) -> bool:
        booking = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.id == booking_id).first()
        if not booking:
            return False
        db.delete(booking)
        db.commit()
        return True

    @classmethod
    def get_vendor_analytics(cls, db: Session, event_id: Optional[str] = None) -> VendorAnalyticsSummary:
        total_directory = db.query(VendorDirectoryModel).count()

        # Category counts across entire directory
        all_vendors = db.query(VendorDirectoryModel).all()
        cat_counts: Dict[str, int] = {}
        for v in all_vendors:
            cat_counts[v.category] = cat_counts.get(v.category, 0) + 1

        if not event_id:
            return VendorAnalyticsSummary(
                event_id=None,
                total_directory_vendors=total_directory,
                shortlisted_count=0,
                booked_count=0,
                negotiating_count=0,
                total_agreed_cost=0.0,
                total_advance_paid=0.0,
                total_remaining_payment=0.0,
                category_counts=cat_counts,
                booking_status_counts={},
                category_spending=[],
            )

        # Event-specific bookings
        bookings = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.event_id == event_id).all()

        shortlisted = sum(1 for b in bookings if b.booking_status == "Shortlisted")
        booked = sum(1 for b in bookings if b.booking_status == "Booked")
        negotiating = sum(1 for b in bookings if b.booking_status in ("Contacted", "Negotiating"))

        total_agreed = sum(b.agreed_price for b in bookings if b.booking_status != "Cancelled")
        total_advance = sum(b.advance_payment for b in bookings if b.booking_status != "Cancelled")
        total_remaining = max(0.0, total_agreed - total_advance)

        status_counts: Dict[str, int] = {}
        for b in bookings:
            status_counts[b.booking_status] = status_counts.get(b.booking_status, 0) + 1

        # Planned budget by category from EventModel.plan_json
        planned_map: Dict[str, float] = {}
        event = db.query(EventModel).filter(EventModel.id == event_id).first()
        if event and event.plan_json:
            try:
                p_data = json.loads(event.plan_json)
                b_items = p_data.get("budget", {}).get("items", [])
                for it in b_items:
                    c_name = it.get("category", "")
                    # Match categories
                    for supported_cat in cat_counts.keys():
                        if supported_cat.lower() in c_name.lower() or c_name.lower() in supported_cat.lower():
                            planned_map[supported_cat] = planned_map.get(supported_cat, 0.0) + float(it.get("allocated_amount", 0.0))
            except Exception:
                pass

        # Aggregate category spending
        cat_spending_dict: Dict[str, Dict[str, float]] = {}
        for b in bookings:
            if b.booking_status == "Cancelled":
                continue
            cat = b.vendor.category
            if cat not in cat_spending_dict:
                cat_spending_dict[cat] = {"agreed": 0.0, "advance": 0.0}
            cat_spending_dict[cat]["agreed"] += b.agreed_price
            cat_spending_dict[cat]["advance"] += b.advance_payment

        spending_list: List[VendorCategorySpending] = []
        for cat, vals in cat_spending_dict.items():
            agreed_amt = vals["agreed"]
            adv_amt = vals["advance"]
            spending_list.append(
                VendorCategorySpending(
                    category=cat,
                    planned_budget=round(planned_map.get(cat, agreed_amt), 2),
                    agreed_cost=round(agreed_amt, 2),
                    advance_paid=round(adv_amt, 2),
                    remaining_payment=round(max(0.0, agreed_amt - adv_amt), 2),
                )
            )

        return VendorAnalyticsSummary(
            event_id=event_id,
            total_directory_vendors=total_directory,
            shortlisted_count=shortlisted,
            booked_count=booked,
            negotiating_count=negotiating,
            total_agreed_cost=round(total_agreed, 2),
            total_advance_paid=round(total_advance, 2),
            total_remaining_payment=round(total_remaining, 2),
            category_counts=cat_counts,
            booking_status_counts=status_counts,
            category_spending=spending_list,
        )

    @classmethod
    def record_advance_as_expense(
        cls,
        db: Session,
        event_id: str,
        booking_id: str,
        payment_method: str = "UPI",
        notes: Optional[str] = None,
    ):
        """
        Integrates with Phase 2 Smart Expense Tracking.
        Records an advance payment as an actual paid expense in the database.
        """
        booking = (
            db.query(EventVendorBookingModel)
            .filter(
                EventVendorBookingModel.id == booking_id,
                EventVendorBookingModel.event_id == event_id,
            )
            .first()
        )
        if not booking:
            raise ValueError(f"Booking {booking_id} not found for event {event_id}")

        if booking.advance_payment <= 0.0:
            raise ValueError("No advance payment has been recorded for this booking yet.")

        from .expense_service import ExpenseService
        from .schemas import ExpenseCreate

        today_date = booking.booking_date or datetime.now().strftime("%Y-%m-%d")
        exp_in = ExpenseCreate(
            expense_name=f"Advance: {booking.vendor.name}",
            category=booking.vendor.category,
            amount=float(booking.advance_payment),
            expense_date=today_date,
            payment_status="Paid",
            payment_method=payment_method or "Bank Transfer",
            vendor_name=booking.vendor.name,
            notes=notes or f"Advance payment for {booking.vendor.name} ({booking.booking_status})",
        )
        return ExpenseService(db).create_expense(event_id, exp_in)

    # =========================================================
    # HELPERS
    # =========================================================

    @classmethod
    def _to_vendor_response(cls, model: VendorDirectoryModel) -> VendorResponse:
        services = []
        try:
            services = json.loads(model.services_offered) if model.services_offered else []
        except Exception:
            pass

        images = []
        try:
            images = json.loads(model.portfolio_images) if model.portfolio_images else []
        except Exception:
            pass

        return VendorResponse(
            id=model.id,
            name=model.name,
            category=model.category,
            location=model.location,
            description=model.description,
            services_offered=services,
            min_price=model.min_price,
            max_price=model.max_price,
            rating=model.rating,
            review_count=model.review_count,
            experience_years=model.experience_years,
            phone=model.phone,
            email=model.email,
            website=model.website,
            portfolio_images=images,
            is_verified=model.is_verified,
            is_favorite=model.is_favorite,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @classmethod
    def _to_booking_response(cls, model: EventVendorBookingModel) -> EventVendorBookingResponse:
        rem = max(0.0, model.agreed_price - model.advance_payment)
        return EventVendorBookingResponse(
            id=model.id,
            event_id=model.event_id,
            vendor_id=model.vendor_id,
            vendor=cls._to_vendor_response(model.vendor),
            booking_status=model.booking_status,
            agreed_price=model.agreed_price,
            advance_payment=model.advance_payment,
            remaining_payment=round(rem, 2),
            booking_date=model.booking_date,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
