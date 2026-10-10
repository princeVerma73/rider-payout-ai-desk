import os
import pandas as pd
from app.db.session import SessionLocal
from app.db.models import init_db, Rider, Trip, PayoutLine

def seed_database():
    # Pehle tables create karo agar nahi bani hain toh
    init_db()
    db = SessionLocal()

    # Agar data pehle se hai, toh wapas seed mat karo
    if db.query(Rider).first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    # Data folder ka sahi path dhoondhna
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, "data")

    # 1. Seed Riders
    riders_path = os.path.join(data_dir, "riders.csv")
    if os.path.exists(riders_path):
        df_riders = pd.read_csv(riders_path)
        df_riders.drop_duplicates(subset=['rider_id'], inplace=True)  # ADDED FIX
        for _, row in df_riders.iterrows():
            db.merge(Rider(
                rider_id=str(row.get("rider_id")),
                name=str(row.get("name", "")),
                phone=str(row.get("phone", "")),
                city=str(row.get("city", ""))
            ))

    # 2. Seed Trips
    trips_path = os.path.join(data_dir, "trips.csv")
    if os.path.exists(trips_path):
        df_trips = pd.read_csv(trips_path)
        df_trips.drop_duplicates(subset=['trip_id'], inplace=True)  # ADDED FIX
        for _, row in df_trips.iterrows():
            db.merge(Trip(
                trip_id=str(row.get("trip_id")),
                rider_id=str(row.get("rider_id")),
                date=str(row.get("date", "")),
                distance_km=float(row.get("distance_km", 0.0)),
                fare=float(row.get("fare", 0.0)),
                status=str(row.get("status", ""))
            ))

    # 3. Seed Payout Lines
    payout_path = os.path.join(data_dir, "payout_lines.csv")
    if os.path.exists(payout_path):
        df_payout = pd.read_csv(payout_path)
        df_payout.drop_duplicates(subset=['line_id'], inplace=True)  # ADDED FIX
        for _, row in df_payout.iterrows():
            db.merge(PayoutLine(
                line_id=str(row.get("line_id")),
                rider_id=str(row.get("rider_id")),
                trip_id=str(row.get("trip_id")) if pd.notna(row.get("trip_id")) else None,
                amount=float(row.get("amount", 0.0)),
                category=str(row.get("category", "")),
                date=str(row.get("date", ""))
            ))

    # Saara data save (commit) karo aur connection close karo
    db.commit()
    db.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()