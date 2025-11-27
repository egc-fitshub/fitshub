from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from app.modules.dataset.models import DataSet, DSMetaData
from core.seeders.BaseSeeder import BaseSeeder


class CommunitySeeder(BaseSeeder):
    def run(self):
        admin_user = User.query.filter_by(email="admin@example.com").first()
        curator_user = User.query.filter_by(email="curator@example.com").first()

        if not admin_user or not curator_user:
            raise Exception(
                "Required users (admin@example.com, curator@example.com) not found. Please seed users first."
            )

        ds1 = DataSet.query.join(DataSet.ds_meta_data).filter(DSMetaData.title == "Sample dataset 1").first()
        ds2 = DataSet.query.join(DataSet.ds_meta_data).filter(DSMetaData.title == "Sample dataset 2").first()
        ds3 = DataSet.query.join(DataSet.ds_meta_data).filter(DSMetaData.title == "Sample dataset 3").first()

        if not ds1 or not ds2 or not ds3:
            print("Warning: Not all required datasets (IDs 1, 2, 3) were found.")

        data = [
            Community(
                name="Test community 1",
                description="This is a test description",
                logo_url="/static/img/photos/communities/logo_ejemplo1.png",
            ),
            Community(
                name="Test community 2",
                description="This is a test description",
                logo_url="/static/img/photos/communities/logo_ejemplo2.png",
            ),
        ]

        seeded_communities = self.seed(data)

        community1 = seeded_communities[0]
        community2 = seeded_communities[1]

        community1.curators.append(admin_user)
        community1.curators.append(curator_user)

        community2.curators.append(admin_user)

        if ds1:
            ds_assoc_1 = CommunityDataSet(community=community1, dataset=ds1, status=CommunityDataSetStatus.ACCEPTED)
            self.seed([ds_assoc_1])

        if ds2:
            ds_assoc_2 = CommunityDataSet(community=community1, dataset=ds2, status=CommunityDataSetStatus.ACCEPTED)
            self.seed([ds_assoc_2])

        if ds3:
            ds_assoc_3 = CommunityDataSet(community=community1, dataset=ds3, status=CommunityDataSetStatus.PENDING)
            self.seed([ds_assoc_3])

        self.db.session.commit()
