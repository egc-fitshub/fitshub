from flask import render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from app.modules.community import community_bp
from app.modules.community.forms import CommunityForm
from app.modules.community.services import CommunityService, CommunityDataSetService
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.services import DataSetService
from app.modules.auth.utils import role_required
from app.modules.auth.models import RoleType 

community_service = CommunityService()
user_service = AuthenticationService()
dataset_service = DataSetService()
community_dataset_service = CommunityDataSetService()


'''
READ ALL
'''
@community_bp.route('/community', methods=['GET'])
def index():
    communities = community_service.get_all_communities()
    return render_template('community/index.html', communities=communities, authorization=False)

'''
GET ALL FROM USER
'''
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
@community_bp.route('/my_communities', methods=['GET'])
def get_communities_user():
    communities = user_service.get_curated_communities_by_id(current_user.id)
    return render_template('community/index.html', communities=communities, authorization=True)

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
        result = community_service.create_from_form(
            form_data=form, 
            logo_file=form.logo_file.data, 
        )
        return community_service.handle_service_response(
            result=result,
            errors=form.errors,
            success_url_redirect='community.index',
            success_msg='Community created successfully!',
            error_template='community/create_community.html',
            form=form
        )
        
    return render_template('community/create_community.html', form=form)

'''
DELETE COMMUNITY
'''
@community_bp.route('/community/<int:community_id>/delete', methods=['POST'])
@login_required
@role_required(roles=[RoleType.ADMINISTRATOR])
def delete_community(community_id):
    result = community_service.delete(community_id)
    if 'error' in result:
        flash(result['error'], 'danger')
    else:
        flash('Community deleted successfully!', 'success')

    return redirect('community/index.html')

'''
UPDATE COMMUNITY
'''
@community_bp.route('/community/<int:community_id>/update', methods=['GET', 'POST'])
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
def update_community(community_id):
    community = community_service.get_or_404(community_id)
    if not community:
        flash('Community not found.', 'danger')
        return redirect('community.index')
    
    form = CommunityForm(obj=community)
    
    form.submit.label.text = 'Update Community' 
    
    if form.validate_on_submit():
        
        result = community_service.update_from_form(
            community_id=community_id, 
            form_data=form, 
            logo_file=form.logo_file.data
        )
        
        return community_service.handle_service_response(
            result=result,
            errors=form.errors,
            success_url_redirect='community.get_communities_user',
            success_msg='Community updated successfully!',
            error_template='community/create_community.html', 
            form=form,
        )

    return render_template('community/create_community.html', form=form, community=community)

'''
PROPOSE DATASET
'''
@community_bp.route('/community/<int:community_id>/propose/<int:dataset_id>', methods=['POST'])
@login_required
def propose_dataset(community_id, dataset_id):
    result = community_service.propose_dataset(community_id, dataset_id)
    community = community_service.get_or_404(community_id)
    
    if 'error' in result:
        flash(result['error'], 'danger')
    else:
        flash('Dataset proposed successfully! It is now pending review by the curators.', 'success')

    return redirect('community/details.html', community=community)

def check_if_dataset_curator(community_id):
    community = community_service.get_or_404(community_id)
    if current_user in community.curators() or current_user.role.value == "administrator":
        return True, community
    
    return False, community

'''
PENDING DATASETS
'''
@community_bp.route('/community/<int:community_id>/review', methods=['GET'])
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
def review_pending_datasets(community_id):
    has_permission, community = check_if_dataset_curator(community_id)
    if not has_permission:
        flash('You have no permission to curate this community')
        return redirect('community/details.html', community=community)

    pending_associations = community_dataset_service.get_pending_datasets(community_id)
    
    pending_datasets = [assoc.dataset for assoc in pending_associations]

    return render_template('community/review.html', community=community, pending_datasets=pending_datasets)

'''
APPROVE DATASET
'''
@community_bp.route('/community/<int:community_id>/approve/<int:dataset_id>', methods=['POST'])
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
def approve_dataset(community_id, dataset_id):
    has_permission, community = check_if_dataset_curator(community_id)
    if not has_permission:
        flash('You have no permission to curate this community')
        return redirect('community/details.html', community=community)
        
    result = community_service.update_dataset_status(
        community_id, 
        dataset_id, 
        "accepted"
    )

    if 'error' in result:
        flash(result['error'], 'danger')
    else:
        flash('Dataset approved and added to the community!', 'success')
    
    return redirect('community/details.html', community=community)

'''
REJECT DATASET
'''
@community_bp.route('/community/<int:community_id>/reject/<int:dataset_id>', methods=['POST'])
@login_required
@role_required(roles=[RoleType.CURATOR, RoleType.ADMINISTRATOR])
def reject_dataset(community_id, dataset_id):
    has_permission, community = check_if_dataset_curator(community_id)
    if not has_permission:
        flash('You have no permission to curate this community')
        return redirect('community/details.html', community=community)
        
    result = community_service.update_dataset_status(
        community_id, 
        dataset_id, 
        "accepted"
    )

    if 'error' in result:
        flash(result['error'], 'danger')
    else:
        flash('Dataset rejected from the community.', 'warning')
        
    return redirect('community/details.html', community=community)