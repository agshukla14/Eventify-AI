import sys
from pathlib import Path
from datetime import date, timedelta

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

from backend.app.database import SessionLocal, Base, engine
from backend.app.schemas import EventIntake
from backend.app.plan_service import PlanService

Base.metadata.create_all(bind=engine)


def seed_all():
    db = SessionLocal()
    plan_service = PlanService(db)
    today = date.today()

    seeds = [
        EventIntake(
            event_type="wedding",
            title="Priya & Rohan Royal Heritage Wedding",
            date=(today + timedelta(days=180)).strftime("%Y-%m-%d"),
            city="Jaipur",
            guest_count=350,
            total_budget=2500000.0,
            currency="INR",
            theme_style="Royal Rajasthani Heritage & Marigolds",
            cultural_preferences="Traditional Marwari Customs & Sangeet Night",
            dietary_preferences=["Vegetarian", "Jain Options"],
            must_haves=["Bespoke Floral Mandap", "Vintage Car Baraat Procession", "Live Folk Sitar Troupe"],
            age_group_details="Multi-generational families, elders, and young friends",
        ),
        EventIntake(
            event_type="birthday",
            title="Kabir's 10th Superhero Birthday Academy",
            date=(today + timedelta(days=25)).strftime("%Y-%m-%d"),
            city="Bengaluru",
            guest_count=45,
            total_budget=65000.0,
            currency="INR",
            theme_style="Avengers Superhero Training Camp",
            cultural_preferences="Fun interactive milestone party",
            dietary_preferences=["Vegetarian", "Nut-Free"],
            must_haves=["Spider-Man 3D Cake", "Obstacle Course", "Hero Cape Favors"],
            age_group_details="Kids aged 9-11 and parents",
        ),
        EventIntake(
            event_type="community",
            title="Indiranagar Green Tech & Eco Festival",
            date=(today + timedelta(days=60)).strftime("%Y-%m-%d"),
            city="Bengaluru",
            guest_count=500,
            total_budget=600000.0,
            currency="INR",
            theme_style="Eco-Innovation & Solar Futures",
            cultural_preferences="Open neighborhood civic festival",
            dietary_preferences=["Vegetarian"],
            must_haves=["Keynote AV Stage", "Solar Power Station", "Waste Segregation Team"],
            age_group_details="Residents, students, and senior citizens",
        ),
    ]

    print("Seeding demo events...")
    for s in seeds:
        plan = plan_service.create_plan(s)
        print(f"Created seed plan: '{plan.intake.title}' (ID: {plan.event_id})")

    db.close()
    print("Seed data successfully created!")


if __name__ == "__main__":
    seed_all()
