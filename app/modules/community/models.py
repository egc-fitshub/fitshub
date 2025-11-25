from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum

from app import db
from app.modules.dataset.models import DataSet

community_curator_association = db.Table(
    "community_curator_association",
    db.Column("community_id", db.Integer, db.ForeignKey("community.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class CommunityDataSetStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class CommunityDataSet(db.Model):
    __tablename__ = "community_dataset_association"

    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), primary_key=True)

    status = db.Column(SQLAlchemyEnum(CommunityDataSetStatus), nullable=False, default=CommunityDataSetStatus.PENDING)

    community = db.relationship("Community", back_populates="dataset_associations")
    dataset = db.relationship("DataSet", back_populates="community_associations")

    def __repr__(self):
        return f"<CommunityDataSet Community={self.community_id} Dataset={self.dataset_id} Status={self.status.value}>"


class Community(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    logo_url = db.Column(db.String(512), nullable=True)

    curators = db.relationship(
        "User",
        secondary="community_curator_association",
        lazy="dynamic",
        backref=db.backref("curated_communities", lazy="dynamic"),
    )

    dataset_associations = db.relationship(
        "CommunityDataSet", back_populates="community", lazy="dynamic", cascade="all, delete-orphan"
    )

    def datasets(self):
        return DataSet.query.join(CommunityDataSet).filter(
            CommunityDataSet.community_id == self.id, CommunityDataSet.status == CommunityDataSetStatus.ACCEPTED
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "logo_url": self.logo_url,
        }

    def __repr__(self):
        return f"Community<{self.id}>: {self.name}"
