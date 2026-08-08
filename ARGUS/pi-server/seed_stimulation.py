import database
import datetime

def seed_database():
    database.init_db()
    db = database.SessionLocal()
    
    # 1. Create a dummy node
    node = database.NodeModel(
        node_id="node-north-01", 
        latitude=-27.4698, 
        longitude=153.0251, 
        status="HEALTHY", 
        battery=95
    )
    db.merge(node)
    db.commit()

    # 2. Seed Risk Assessments following the escalation path
    stages = ["LOW", "LOW", "GUARDED", "ELEVATED", "HIGH", "CRITICAL"]
    
    for i, stage in enumerate(stages):
        risk = database.RiskAssessmentModel(
            timestamp=datetime.datetime.utcnow() - datetime.timedelta(minutes=(len(stages) - i) * 30),
            region="North Sector",
            hazard="bushfire",
            risk_level=stage,
            confidence=0.75 + (i * 0.04),
            explanation=f"Automated risk evaluation step {i+1} with level {stage}.",
            recommendation="Increase monitoring and prepare local warning protocols."
        )
        db.add(risk)
    
    db.commit()
    db.close()
    print("Database successfully seeded with simulation data!")

if __name__ == "__main__":
    seed_database()
