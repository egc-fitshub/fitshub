from flask import render_template, request
from flask_login import login_required
from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm
from app.modules.community.services import CommunityService
from app.modules.auth.services import AuthenticationService
from app.modules.auth.utils import role_required
from app.modules.auth.models import RoleType
from app.modules.auth.models import User 

community_service = CommunityService()
user_service = AuthenticationService()


'''
READ ALL
'''
@community_bp.route('/community', methods=['GET'])
def index():
    form = CommunityForm()
    communities = community_service.get_all_communities()
    return render_template('community/index.html', communities=communities, form=form)

'''
READ BY ID
'''
@community_bp.route('/community/<int:community_id>', methods=['GET'])
def get_community(community_id):
    community = community_service.get_or_404(community_id)

    return render_template('community/details.html', community=community)

'''
CREATE
'''
def populate_curator_choices(form):
    curators = user_service.get_curators()
    form.curator_ids.choices = [(str(u.id), u.email) for u in curators]
    
@community_bp.route('/community/create', methods=['GET', 'POST'])
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
def create_community():
    form = CommunityForm()
    populate_curator_choices(form)
        
    if form.validate_on_submit():
        result = community_service.create(
            form_data=form, 
            logo_file=form.logo_file.data, 
        )
        return community_service.handle_service_response(
            result=result,
            errors=form.errors,
            success_url_redirect='community.index',
            success_msg='Community created successfully!',
            error_template='community/create.html',
            form=form
        )
    
    
    
    return render_template('community/create.html', form=form)