"""
Idempotent seed script for CivicPulse.

Run twice safely: each complaint carries a stable `seed_key` embedded
in its text as a hidden marker, so re-running this script checks for
that marker before inserting, rather than blindly appending duplicates.
"""

from app.db import SessionLocal
from app.repositories.models import Complaint
from app.schemas import Category, Priority, Status

# Each tuple: (seed_key, text, location, category, priority)
SEED_COMPLAINTS = [
    ("seed-001", "Water supply not coming since 3 days in our gali, bohat problem ho rahi hai", "Block C, Model Town, Lahore", Category.water, Priority.high),
    ("seed-002", "Bijli ka connection kal se off hai, transformer shayad kharab ho gaya", "Sector I-8, Islamabad", Category.electricity, Priority.high),
    ("seed-003", "Garbage collection nahi hua is hafte, bohat bad smell aa rahi hai", "Gulshan-e-Iqbal Block 6, Karachi", Category.sanitation, Priority.normal),
    ("seed-004", "Road pe bara gaddha ban gaya hai, motorcycle wale gir jate hain", "Main Boulevard, Bahadurabad, Karachi", Category.roads, Priority.high),
    ("seed-005", "Streetlight bund hai teen hafton se, raat ko andhera rehta hai", "Street 14, F-10/2, Islamabad", Category.streetlights, Priority.normal),
    ("seed-006", "Sewerage line block hai, pani gali mein bhar gaya hai", "Liaquatabad Block 2, Karachi", Category.sanitation, Priority.high),
    ("seed-007", "Water pipe leak ho raha hai footpath ke neeche, paani waste ho raha", "Johar Town Phase 2, Lahore", Category.water, Priority.normal),
    ("seed-008", "Voltage bohat kam aata hai, appliances kharab ho rahe hain", "Satellite Town, Rawalpindi", Category.electricity, Priority.normal),
    ("seed-009", "Traffic signal kaam nahi kar raha chowk pe, accident ka khatra hai", "Faisal Chowk, Rawalpindi", Category.roads, Priority.high),
    ("seed-010", "Kachra utha nahi is area mein, container overflow ho gaya", "North Nazimabad Block H, Karachi", Category.sanitation, Priority.normal),
    ("seed-011", "Pole se sparks nikal rahe hain, bacchon ko khatra hai", "Township, Lahore", Category.electricity, Priority.high),
    ("seed-012", "Road resurfacing ka kaam adhoora chor diya, dust bohat udd rahi hai", "GT Road, Gujranwala", Category.roads, Priority.normal),
    ("seed-013", "Water tanker book kiya tha, teen din se nahi aaya", "DHA Phase 5, Karachi", Category.water, Priority.normal),
    ("seed-014", "Streetlight khambe latak rahe hain, gir sakte hain", "Wapda Town, Lahore", Category.streetlights, Priority.high),
    ("seed-015", "Manhole cover missing hai, raat ko koi gir sakta hai", "Shahra-e-Faisal, Karachi", Category.sanitation, Priority.high),
    ("seed-016", "Meter reading galat aa rahi, bill bohat zyada hai is dafa", "PECHS Block 6, Karachi", Category.electricity, Priority.low),
    ("seed-017", "Speed breaker bina paint ke hai, raat ko nazar nahi aata", "Cavalry Ground, Lahore", Category.roads, Priority.normal),
    ("seed-018", "Water quality theek nahi lagti, badbu aa rahi hai nal ke pani se", "Latifabad Unit 7, Hyderabad", Category.water, Priority.high),
    ("seed-019", "Park mein streetlights sab band hain, security issue hai", "F-9 Park, Islamabad", Category.streetlights, Priority.normal),
    ("seed-020", "Encroachment footpath pe hai, pedestrians road pe walk karte hain", "Anarkali Bazaar, Lahore", Category.other, Priority.low),
    ("seed-021", "Sewerage overflow ho raha hai school ke samne", "Malir Cantt, Karachi", Category.sanitation, Priority.high),
    ("seed-022", "Underground cable fault hai, poori colony ki bijli gayi hui hai", "Cantt Area, Multan", Category.electricity, Priority.high),
    ("seed-023", "Road pe crack ban gaye hain baarish ke baad", "Askari 10, Lahore", Category.roads, Priority.low),
    ("seed-024", "Water line new connection ki application pending hai do mahine se", "Korangi, Karachi", Category.water, Priority.low),
    ("seed-025", "Streetlight timer sahi kaam nahi karta, din mein bhi jalti rehti hai", "Bahria Town Phase 4, Rawalpindi", Category.streetlights, Priority.low),
    ("seed-026", "Stray dogs ka masla hai park mein, bachon ko khatra hai", "Clifton Block 5, Karachi", Category.other, Priority.normal),
    ("seed-027", "Bijli ke bill mein extra charges add ho gaye bina wajah", "Samanabad, Lahore", Category.electricity, Priority.low),
    ("seed-028", "Road divider tota hua hai, traffic wrong side se aa jata hai", "Airport Road, Peshawar", Category.roads, Priority.high),
    ("seed-029", "Water pressure bohat kam hai upper floor ke liye", "Gulberg 3, Lahore", Category.water, Priority.normal),
    ("seed-030", "Garbage truck route change ho gaya bina notice ke", "Saddar, Rawalpindi", Category.sanitation, Priority.low),
    ("seed-031", "Naya transformer lagne ke baad bhi load-shedding same hai", "Officers Colony, Sialkot", Category.electricity, Priority.normal),
    ("seed-032", "Footpath tiles ukhri hui hain, walk karna mushkil hai", "Blue Area, Islamabad", Category.roads, Priority.low),
]


def run_seed() -> None:
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for seed_key, text, location, category, priority in SEED_COMPLAINTS:
            marked_text = f"[{seed_key}] {text}"

            exists = (
                db.query(Complaint)
                .filter(Complaint.text.like(f"[{seed_key}]%"))
                .first()
            )
            if exists is not None:
                skipped += 1
                continue

            complaint = Complaint(
                text=marked_text,
                location=location,
                reporter_contact=None,
                category=category,
                priority=priority,
                status=Status.open,
                ai_summary=None,
                triaged_by="rules",
                triage_latency_ms=0,
            )
            db.add(complaint)
            inserted += 1

        db.commit()
        print(f"Seed complete: {inserted} inserted, {skipped} already present (skipped).")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()