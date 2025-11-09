from app.modules.auth.models import RoleType, User
from app.modules.profile.models import UserProfile
from core.repositories.BaseRepository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def create(self, commit: bool = True, **kwargs):
        password = kwargs.pop("password")
        instance = self.model(**kwargs)
        instance.set_password(password)
        self.session.add(instance)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return instance

    def get_by_email(self, email: str):
        return self.model.query.filter_by(email=email).first()

    def get_roles(self):
        return (
            self.session.query(self.model.id, self.model.email, self.model.role, UserProfile.name, UserProfile.surname)
            .join(UserProfile, self.model.id == UserProfile.user_id)
            .filter(self.model.role != RoleType.ADMINISTRATOR)
            .all()
        )
