document.addEventListener('DOMContentLoaded', () => {
    bindFilters();
    setupDateValidation();
    runSearch(); // initial load
});

function createKiIcon(iconName, pathCount) {
    const icon = document.createElement('i');
    icon.className = `ki-duotone ${iconName}`;

    for (let idx = 1; idx <= pathCount; idx++) {
        const span = document.createElement('span');
        span.className = `path${idx}`;
        icon.appendChild(span);
    }

    return icon;
}

function createDatasetCard(dataset, assets) {
    const row = document.createElement('div');
    row.className = 'row';

    const col = document.createElement('div');
    col.className = 'col-12 mb-5';
    row.appendChild(col);

    const card = document.createElement('div');
    card.className = 'card';
    col.appendChild(card);

    const body = document.createElement('div');
    body.className = 'card-body';
    card.appendChild(body);

    // Header with title and badge
    const header = document.createElement('div');
    header.className = 'd-flex align-items-center justify-content-between';
    body.appendChild(header);

    const titleEl = document.createElement('h2');
    titleEl.className = 'mb-0';
    const titleLink = document.createElement('a');
    titleLink.href = dataset.url || '#';
    titleLink.textContent = dataset.title || '';
    titleEl.appendChild(titleLink);
    header.appendChild(titleEl);

    const badge = document.createElement('span');
    badge.className = 'badge bg-secondary';
    badge.textContent = dataset.publication_type_label || '';
    header.appendChild(badge);

    // Created at information
    const createdAt = document.createElement('p');
    createdAt.className = 'text-muted mt-2 mb-1';
    createdAt.textContent = dataset.created_at || '';
    body.appendChild(createdAt);

    // Authors list
    if (Array.isArray(dataset.authors) && dataset.authors.length > 0) {
        const authorsRow = document.createElement('div');
        authorsRow.className = 'row mb-3';
        body.appendChild(authorsRow);

        const authorsCol = document.createElement('div');
        authorsCol.className = 'col-12';
        authorsRow.appendChild(authorsCol);

        const authorList = document.createElement('ul');
        authorList.className = 'list-unstyled mb-0';
        authorList.style.fontSize = '0.85rem';
        authorsCol.appendChild(authorList);

        dataset.authors.forEach(author => {
            const li = document.createElement('li');
            li.className = 'd-flex align-items-center mb-1';
            li.style.lineHeight = '1.2';

            const userIcon = createKiIcon('ki-user', 2);
            li.appendChild(userIcon);

            const spacer = document.createTextNode('\u00A0');
            li.appendChild(spacer);

            const nameSpan = document.createElement('span');
            nameSpan.className = 'me-2';
            nameSpan.textContent = author?.name || '';
            li.appendChild(nameSpan);

            if (author?.affiliation) {
                const affiliationBadge = document.createElement('span');
                affiliationBadge.className = 'badge bg-light text-muted me-2';
                affiliationBadge.style.fontSize = '0.75rem';
                affiliationBadge.textContent = author.affiliation;
                li.appendChild(affiliationBadge);
            }

            if (author?.orcid) {
                const orcidLink = document.createElement('a');
                orcidLink.href = `https://orcid.org/${encodeURIComponent(author.orcid)}`;
                orcidLink.target = '_blank';
                orcidLink.className = 'text-success d-flex align-items-center';
                orcidLink.setAttribute('data-bs-toggle', 'tooltip');
                orcidLink.setAttribute('data-bs-placement', 'top');
                orcidLink.title = `ORCID: ${author.orcid}`;

                if (assets.orcidIcon) {
                    const orcidImg = document.createElement('img');
                    orcidImg.src = assets.orcidIcon;
                    orcidImg.alt = 'ORCID';
                    orcidImg.className = 'me-1';
                    orcidImg.width = 14;
                    orcidImg.height = 14;
                    orcidLink.appendChild(orcidImg);
                }

                li.appendChild(orcidLink);
            }

            authorList.appendChild(li);
        });
    }

    // Description
    if (dataset.description) {
        const descriptionRow = document.createElement('div');
        descriptionRow.className = 'row mb-2';
        body.appendChild(descriptionRow);

        const descriptionCol = document.createElement('div');
        descriptionCol.className = 'col-12';
        descriptionRow.appendChild(descriptionCol);

        const description = document.createElement('p');
        description.className = 'card-text';
        description.innerHTML = dataset.description;
        descriptionCol.appendChild(description);
    }

    // Tags
    const tags = Array.isArray(dataset.tags)
        ? dataset.tags
        : typeof dataset.tags === 'string' && dataset.tags
        ? dataset.tags.split(',').map(tag => tag.trim()).filter(Boolean)
        : [];

    if (tags.length > 0) {
        const tagsRow = document.createElement('div');
        tagsRow.className = 'row mb-3';
        body.appendChild(tagsRow);

        const tagsCol = document.createElement('div');
        tagsCol.className = 'col-12';
        tagsRow.appendChild(tagsCol);

        tags.forEach(tag => {
            const tagBadge = document.createElement('span');
            tagBadge.className = 'badge bg-secondary me-1';
            tagBadge.textContent = tag;
            tagsCol.appendChild(tagBadge);
        });
    }

    // Action buttons
    const actionRow = document.createElement('div');
    actionRow.className = 'row mt-4';
    body.appendChild(actionRow);

    const actionCol = document.createElement('div');
    actionCol.className = 'col-12';
    actionRow.appendChild(actionCol);

    const viewButton = document.createElement('a');
    viewButton.href = dataset.url || '#';
    viewButton.className = 'btn btn-outline-secondary btn-xs me-2 d-inline-flex align-items-center';
    viewButton.style.fontSize = '0.75rem';
    viewButton.style.padding = '0.25rem 0.5rem';
    viewButton.style.borderRadius = '4px';

    const viewIcon = createKiIcon('ki-eye', 3);
    viewButton.appendChild(viewIcon);
    viewButton.appendChild(document.createTextNode('View'));
    actionCol.appendChild(viewButton);

    const downloadButton = document.createElement('a');
    downloadButton.href = `/datasets/download/${encodeURIComponent(dataset.id)}`;
    downloadButton.className = 'btn btn-outline-secondary btn-xs d-inline-flex align-items-center';
    downloadButton.style.fontSize = '0.75rem';
    downloadButton.style.padding = '0.25rem 0.5rem';
    downloadButton.style.borderRadius = '4px';

    const downloadIcon = createKiIcon('ki-folder-down', 2);
    downloadButton.appendChild(downloadIcon);
    const sizeLabel = dataset.total_size_in_human_format ? ` (${dataset.total_size_in_human_format})` : '';
    downloadButton.appendChild(document.createTextNode(`Download${sizeLabel}`));
    actionCol.appendChild(downloadButton);

    // DOI section
    const doiRow = document.createElement('div');
    doiRow.className = 'row mt-3';
    body.appendChild(doiRow);

    const doiCol = document.createElement('div');
    doiCol.className = 'col-12 d-flex align-items-center flex-wrap';
    doiRow.appendChild(doiCol);

    const doiLabel = document.createElement('span');
    doiLabel.className = 'px-3 py-1 bg-dark text-white fw-bold rounded-start';
    doiLabel.style.fontFamily = 'monospace';
    doiLabel.textContent = 'DOI';
    doiCol.appendChild(doiLabel);

    const doiLink = document.createElement('a');
    doiLink.href = dataset.url || '#';
    doiLink.target = '_blank';
    doiLink.className = 'px-3 py-1 text-white fw-semibold text-decoration-none rounded-end me-2';
    doiLink.style.background = 'linear-gradient(90deg, #2176bd 0%, #2980b9 100%)';
    doiLink.style.fontFamily = 'monospace';
    doiLink.textContent = dataset.url || '';
    doiCol.appendChild(doiLink);

    const clipboardIcon = document.createElement('i');
    clipboardIcon.dataset.feather = 'clipboard';
    clipboardIcon.className = 'center-button-icon';
    clipboardIcon.style.cursor = 'pointer';
    clipboardIcon.setAttribute('data-bs-toggle', 'tooltip');
    clipboardIcon.title = 'Copy DOI';
    clipboardIcon.addEventListener('click', () => copyText(`dataset_doi_${dataset.id}`));
    doiCol.appendChild(clipboardIcon);

    const hiddenDoi = document.createElement('div');
    hiddenDoi.id = `dataset_doi_${dataset.id}`;
    hiddenDoi.style.display = 'none';
    hiddenDoi.textContent = dataset.url || '';
    doiCol.appendChild(hiddenDoi);

    return row;
}

function createHubfileCard(hubfile) {
    const row = document.createElement('div');
    row.className = 'row';

    const col = document.createElement('div');
    col.className = 'col-12 mb-5';
    row.appendChild(col);

    const card = document.createElement('div');
    card.className = 'card';
    col.appendChild(card);

    const body = document.createElement('div');
    body.className = 'card-body';
    card.appendChild(body);

    const header = document.createElement('div');
    header.className = 'd-flex align-items-center justify-content-between';
    body.appendChild(header);

    const titleEl = document.createElement('h2');
    titleEl.className = 'mb-0';
    titleEl.style.wordBreak = 'break-all';
    const titleLink = document.createElement('a');
    titleLink.href = hubfile.url || '#';
    titleLink.textContent = hubfile.filename || '';
    titleEl.appendChild(titleLink);
    header.appendChild(titleEl);

    const badge = document.createElement('span');
    badge.className = 'badge bg-primary';
    badge.textContent = 'FITS file';
    header.appendChild(badge);

    const datasetInfo = document.createElement('p');
    datasetInfo.className = 'text-muted mt-2 mb-1';
    datasetInfo.textContent = 'Belongs to ';

    if (hubfile.dataset_doi) {
        const datasetLink = document.createElement('a');
        datasetLink.href = hubfile.dataset_doi;
        datasetLink.textContent = hubfile.dataset_title || hubfile.dataset_doi;
        datasetInfo.appendChild(datasetLink);
    } else {
        datasetInfo.appendChild(document.createTextNode(hubfile.dataset_title || ''));
    }

    body.appendChild(datasetInfo);

    const metaRow = document.createElement('div');
    metaRow.className = 'd-flex flex-wrap align-items-center mb-3';
    metaRow.style.gap = '1rem';
    body.appendChild(metaRow);

    if (hubfile.size_in_human_format) {
        const sizeBadge = document.createElement('span');
        sizeBadge.className = 'badge bg-light text-muted';
        sizeBadge.textContent = `Size: ${hubfile.size_in_human_format}`;
        metaRow.appendChild(sizeBadge);
    }

    const buttonsWrapper = document.createElement('div');
    buttonsWrapper.className = 'mt-3';
    body.appendChild(buttonsWrapper);

    const viewButton = document.createElement('button');
    viewButton.onclick = () => window.viewFile(hubfile.id);
    viewButton.className = 'btn btn-outline-secondary btn-xs me-2 d-inline-flex align-items-center';
    viewButton.style.fontSize = '0.75rem';
    viewButton.style.padding = '0.25rem 0.5rem';
    viewButton.style.borderRadius = '4px';

    const viewIcon = createKiIcon('ki-eye', 3);
    viewButton.appendChild(viewIcon);
    viewButton.appendChild(document.createTextNode('View'));
    buttonsWrapper.appendChild(viewButton);

    const downloadButton = document.createElement('a');
    downloadButton.href = `/file/download/${encodeURIComponent(hubfile.id)}`;
    downloadButton.className = 'btn btn-outline-secondary btn-xs d-inline-flex align-items-center';
    downloadButton.style.fontSize = '0.75rem';
    downloadButton.style.padding = '0.25rem 0.5rem';
    downloadButton.style.borderRadius = '4px';

    const downloadIcon = createKiIcon('ki-folder-down', 2);
    downloadButton.appendChild(downloadIcon);
    const hubfileSizeLabel = hubfile.size_in_human_format ? ` (${hubfile.size_in_human_format})` : '';
    downloadButton.appendChild(document.createTextNode(`Download${hubfileSizeLabel}`));
    buttonsWrapper.appendChild(downloadButton);

    return row;
}

function setupDateValidation() {
    const fromInput = document.getElementById('filter-date-from');
    const toInput = document.getElementById('filter-date-to');
    const dateError = document.getElementById('date-error');

    if (!fromInput || !toInput) return;

    const validate = () => {
        const from = new Date(fromInput.value);
        const to = new Date(toInput.value);

        if (fromInput.value && toInput.value && to < from) {
            dateError.classList.remove('d-none');
            toInput.classList.add('is-invalid');
        } else {
            dateError.classList.add('d-none');
            toInput.classList.remove('is-invalid');
        }
    };

    fromInput.addEventListener('change', validate);
    toInput.addEventListener('change', validate);
}

function bindFilters() {
    const filters = [
        '#search-query-filter',
        '#filter-publication-type',
        '#filter-sorting',
        '#filter-tags',
        '#filter-date-from',
        '#filter-date-to'
    ];

    const scheduleSearch = (immediate = false) => {
        if (immediate) {
            clearTimeout(searchDebounceTimer);
            runSearch(true);
            return;
        }

        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => runSearch(true), 250);
    };

    filters.forEach(selector => {
        const el = document.querySelector(selector);
        if (el) {
            el.addEventListener('input', () => scheduleSearch());
            el.addEventListener('change', () => scheduleSearch(true));
        }
    });

    document.getElementById('clear-filters').addEventListener('click', event => {
        event.preventDefault();
        document.getElementById('search-query-filter').value = '';
        document.getElementById('filter-publication-type').value = '';
        document.getElementById('filter-sorting').value = 'newest';
        document.getElementById('filter-tags').value = '';
        document.getElementById('filter-date-from').value = '';
        document.getElementById('filter-date-to').value = '';
        scheduleSearch(true);
    });
}

function setPublicationTypeFilter(type) {
    document.getElementById('filter-publication-type').value = type;
    runSearch();
}

function addTextToQuery(q) {
    document.getElementById('search-query-filter').value = q;
    runSearch();
}

function addTagToQuery(tag) {
    document.getElementById('filter-tags').value = tag;
    runSearch();
}

window.setPublicationTypeFilter = setPublicationTypeFilter;
window.addTagToQuery = addTagToQuery;
window.addTextToQuery = addTextToQuery;

let currentPage = 1;
const pageSize = 10;
let loading = false;
const ERROR_BANNER_ID = 'search-error-banner';
let currentSearchController = null;
let searchDebounceTimer = null;

function clearSearchError() {
    const banner = document.getElementById(ERROR_BANNER_ID);
    if (banner) {
        banner.remove();
    }
}

function showSearchError(message) {
    const container = document.getElementById('results-container');
    const notFound = document.getElementById('no-results');

    if (!container) return;

    notFound?.classList.add('d-none');
    container.innerHTML = '';

    const alert = document.createElement('div');
    alert.id = ERROR_BANNER_ID;
    alert.className = 'alert alert-danger';
    alert.textContent = message || 'Search failed';
    container.appendChild(alert);
}

function runSearch(reset = true) {
    if (reset && typeof reset.preventDefault === 'function') {
        reset.preventDefault();
        reset = true;
    }

    const shouldReset = reset === true;

    const fromInput = document.getElementById('filter-date-from');
    const toInput = document.getElementById('filter-date-to');
    const dateError = document.getElementById('date-error');

    // Validación del rango de fechas
    const fromDate = fromInput.value ? new Date(fromInput.value) : null;
    const toDate = toInput.value ? new Date(toInput.value) : null;

    if (fromDate && toDate && toDate < fromDate) {
        dateError?.classList.remove('d-none');
        toInput.classList.add('is-invalid');
        return;
    }

    dateError?.classList.add('d-none');
    toInput.classList.remove('is-invalid');

    if (!shouldReset && loading) {
        return;
    }

    if (shouldReset) {
        if (currentSearchController) {
            currentSearchController.abort();
            currentSearchController = null;
        }
        loading = false;
        currentPage = 1;
        document.getElementById('results-container').innerHTML = '';
    }

    clearSearchError();

    const queryInput = document.getElementById('search-query-filter');
    const query = queryInput ? queryInput.value.trim() : '';
    const publication_type = document.getElementById('filter-publication-type').value;
    const sorting = document.getElementById('filter-sorting').value;
    const tags = document.getElementById('filter-tags').value.trim();
    const date_from = fromInput.value;
    const date_to = toInput.value;

    const params = new URLSearchParams({
        q: query,
        publication_type: publication_type,
        sorting: sorting,
        page: currentPage,
        size: pageSize
    });

    if (tags) params.append('tags', tags);
    if (date_from) params.append('date_from', date_from);
    if (date_to) params.append('date_to', date_to);

    const controller = new AbortController();
    currentSearchController = controller;
    loading = true;

    fetch(`/api/v1/search?${params.toString()}`, { signal: controller.signal })
        .then(async res => {
            let payload = null;
            try {
                payload = await res.json();
            } catch (parseError) {
                if (!res.ok) {
                    throw new Error('Search service unavailable');
                }
                throw parseError;
            }

            if (!res.ok) {
                const error = new Error(payload?.error || 'Search failed');
                error.details = payload;
                throw error;
            }

            return payload;
        })
        .then(data => {
            renderResults(data.results || [], !shouldReset);
            if (Array.isArray(data.results) && data.results.length > 0) {
                currentPage++;
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') {
                return;
            }
            console.error('Search failed', err);
            showSearchError(err.details?.error || err.message);
        })
        .finally(() => {
            if (currentSearchController === controller) {
                currentSearchController = null;
                loading = false;
            }
        });
}


window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200) {
        runSearch(false); // carga más sin resetear
    }
});


function renderResults(results, append = false) {
    const container = document.getElementById('results-container');
    const notFound = document.getElementById('no-results');
    const assets = {
        orcidIcon: container?.dataset?.orcidIcon || ''
    };

    clearSearchError();

    if (!append) {
        container.innerHTML = '';
    }

    if (!results || results.length === 0) {
        if (!append) notFound.classList.remove('d-none');
        return;
    }

    notFound.classList.add('d-none');

    results.forEach(result => {
        if (result.type === 'dataset') {
            const card = createDatasetCard(result, assets);
            container.appendChild(card);
        } else if (result.type === 'hubfile') {
            const card = createHubfileCard(result);
            container.appendChild(card);
        }
    });

    // Reprocesar iconos Keen
    if (typeof KTIcon !== 'undefined' && KTIcon.update) {
        KTIcon.update();
    }

    if (window.feather && typeof window.feather.replace === 'function') {
        window.feather.replace();
    }

    // Reprocesar tooltips Bootstrap
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
}