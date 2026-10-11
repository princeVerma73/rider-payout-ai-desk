from app.db.session import SessionLocal
from app.db.models import Rider, Trip, PayoutLine
from langchain_core.tools import tool

@tool
def get_rider_details(rider_id: str) -> str:
    """
    Use this tool to get the basic details (name, city, phone) of a rider by their rider_id.
    Call this when you need to verify if a rider exists or need their contact info.
    """
    db = SessionLocal()
    try:
        rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
        if rider:
            return f"Rider {rider.rider_id} details: Name={rider.name}, City={rider.city}, Phone={rider.phone}"
        return f"No rider found with ID {rider_id}"
    except Exception as e:
        return f"Error fetching rider: {str(e)}"
    finally:
        db.close()

@tool
def get_trip_details(trip_id: str) -> str:
    """
    Use this tool to get details of a specific trip (status, distance, fare, rider_id) by its trip_id.
    Call this when a rider asks about a specific trip to check if it was completed, cancelled, or failed.
    """
    db = SessionLocal()
    try:
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if trip:
            return (f"Trip {trip.trip_id} details: Rider={trip.rider_id}, "
                    f"Distance={trip.distance_km}km, Fare={trip.fare}, Status={trip.status}")
        return f"No trip found with ID {trip_id}"
    except Exception as e:
        return f"Error fetching trip: {str(e)}"
    finally:
        db.close()
        
@tool
def check_payout_history(rider_id: str) -> str:
    """
    Use this tool to check all previous payout lines (refunds, penalties, earnings) for a specific rider.
    Call this to verify if a refund for a specific trip has already been processed before.
    """
    db = SessionLocal()
    try:
        payouts = db.query(PayoutLine).filter(PayoutLine.rider_id == rider_id).all()
        if not payouts:
            return f"No payout history found for Rider {rider_id}."
        
        history = []
        for p in payouts:
            history.append(f"[LineID: {p.line_id}, Trip: {p.trip_id}, Amount: {p.amount}, Category: {p.category}]")
        
        return "Payout History:\n" + "\n".join(history)
    except Exception as e:
        return f"Error fetching payouts: {str(e)}"
    finally:
        db.close()