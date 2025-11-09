from app.modules.auth.models import RoleType, User
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder


class AuthSeeder(BaseSeeder):
    priority = 1  # Higher priority

    def run(self):
        # Seeding users
        users = [
            User(email="user1@example.com", password="1234", role=RoleType.USER),
            User(email="user2@example.com", password="1234", role=RoleType.USER),
            User(email="admin@example.com", password="1234", role=RoleType.ADMINISTRATOR),
            User(email="curator@example.com", password="1234", role=RoleType.CURATOR),
            User(email="user@example.com", password="1234", role=RoleType.USER),
        ]

        # Inserted users with their assigned IDs are returned by `self.seed`.
        seeded_users = self.seed(users)

        # Create profiles for each user inserted.
        user_profiles = []
        names = [
            ("John", "Doe"),  # User
            ("Jane", "Doe"),  # User
            ("Arthur", "Pendleton"),  # Admin
            ("Eleanor", "Vance"),  # Curator
            ("John", "Smith"),  # User
        ]

        for user, name in zip(seeded_users, names):
            profile_data = {
                "user_id": user.id,
                "orcid": "",
                "affiliation": "Some University",
                "name": name[0],
                "surname": name[1],
            }
            user_profile = UserProfile(**profile_data)
            user_profiles.append(user_profile)

        # Seeding user profiles
        self.seed(user_profiles)
