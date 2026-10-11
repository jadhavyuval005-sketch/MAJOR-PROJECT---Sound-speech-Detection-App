from datetime import datetime, timezone

from .extensions import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="parent")  # parent | clinician
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=now)
    children = db.relationship("Child", backref="owner", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


class Child(db.Model):
    __tablename__ = "children"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    age_months = db.Column(db.Integer, nullable=False)
    home_language = db.Column(db.String(20), nullable=False, default="mixed")  # hi | en | mixed
    created_at = db.Column(db.DateTime, default=now)
    assessments = db.relationship("Assessment", backref="child", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age_months": self.age_months,
            "home_language": self.home_language,
        }


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False, index=True)
    language = db.Column(db.String(20), nullable=False)  # hi | en | mixed
    status = db.Column(db.String(20), nullable=False, default="in_progress")
    analyzer = db.Column(db.String(30), nullable=False, default="quality")
    created_at = db.Column(db.DateTime, default=now)
    completed_at = db.Column(db.DateTime)
    recordings = db.relationship(
        "Recording", backref="assessment", cascade="all, delete-orphan", order_by="Recording.id"
    )

    def summary(self):
        """Overall score and risk band, computed from whatever has been scored so far."""
        scores = [r.final_score for r in self.recordings if r.final_score is not None]
        if not scores:
            return {"score": None, "band": "not_scored", "scored": 0}
        score = sum(scores) / len(scores)
        band = "typical" if score >= 0.85 else "monitor" if score >= 0.6 else "refer"
        return {"score": round(score, 3), "band": band, "scored": len(scores)}

    def to_dict(self, with_recordings=False):
        d = {
            "id": self.id,
            "child_id": self.child_id,
            "language": self.language,
            "status": self.status,
            "analyzer": self.analyzer,
            "created_at": self.created_at.isoformat() + "Z",
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "recording_count": len(self.recordings),
            **self.summary(),
        }
        if with_recordings:
            d["recordings"] = [r.to_dict() for r in self.recordings]
        return d


class Recording(db.Model):
    __tablename__ = "recordings"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False, index=True)
    word_id = db.Column(db.String(40), nullable=False)
    audio_key = db.Column(db.String(255), nullable=False)
    duration_s = db.Column(db.Float)
    quality_flags = db.Column(db.JSON, default=list)
    auto_score = db.Column(db.Float)  # None when the analyzer cannot score
    recognized = db.Column(db.String(200))
    errors = db.Column(db.JSON, default=list)
    clinician_correct = db.Column(db.Boolean)  # manual override by parent/clinician
    created_at = db.Column(db.DateTime, default=now)

    @property
    def final_score(self):
        if self.clinician_correct is not None:
            return 1.0 if self.clinician_correct else 0.0
        return self.auto_score

    def to_dict(self):
        return {
            "id": self.id,
            "word_id": self.word_id,
            "duration_s": self.duration_s,
            "quality_flags": self.quality_flags or [],
            "auto_score": self.auto_score,
            "recognized": self.recognized,
            "errors": self.errors or [],
            "clinician_correct": self.clinician_correct,
            "final_score": self.final_score,
        }
