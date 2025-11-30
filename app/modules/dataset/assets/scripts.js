var currentId = 0;
        var amount_authors = 0;

        function show_upload_dataset() {
            document.getElementById("upload_dataset").style.display = "block";
        }

        function generateIncrementalId() {
            return currentId++;
        }

        function addField(newAuthor, name, text, className = 'col-lg-6 col-12 mb-3') {
            let fieldWrapper = document.createElement('div');
            fieldWrapper.className = className;

            let label = document.createElement('label');
            label.className = 'form-label';
            label.for = name;
            label.textContent = text;

            let field = document.createElement('input');
            field.name = name;
            field.className = 'form-control';

            fieldWrapper.appendChild(label);
            fieldWrapper.appendChild(field);
            newAuthor.appendChild(fieldWrapper);
        }

        function addRemoveButton(newAuthor) {
            let buttonWrapper = document.createElement('div');
            buttonWrapper.className = 'col-12 mb-2';

            let button = document.createElement('button');
            button.textContent = 'Remove author';
            button.className = 'btn btn-danger btn-sm';
            button.type = 'button';
            button.addEventListener('click', function (event) {
                event.preventDefault();
                newAuthor.remove();
            });

            buttonWrapper.appendChild(button);
            newAuthor.appendChild(buttonWrapper);
        }

        function createAuthorBlock(idx, suffix) {
            let newAuthor = document.createElement('div');
            newAuthor.className = 'author row';
            newAuthor.style.cssText = "border:2px dotted #ccc;border-radius:10px;padding:10px;margin:10px 0; background-color: white";

            addField(newAuthor, `${suffix}authors-${idx}-name`, 'Name *');
            addField(newAuthor, `${suffix}authors-${idx}-affiliation`, 'Affiliation');
            addField(newAuthor, `${suffix}authors-${idx}-orcid`, 'ORCID');
            addRemoveButton(newAuthor);

            return newAuthor;
        }

        function check_title_and_description() {
            let titleInput = document.querySelector('input[name="title"]');
            let descriptionTextarea = document.querySelector('textarea[name="desc"]');

            titleInput.classList.remove("error");
            descriptionTextarea.classList.remove("error");
            clean_upload_errors();

            let titleLength = titleInput.value.trim().length;
            let descriptionLength = descriptionTextarea.value.trim().length;

            if (titleLength < 3) {
                write_upload_error("title must be of minimum length 3");
                titleInput.classList.add("error");
            }

            if (descriptionLength < 3) {
                write_upload_error("description must be of minimum length 3");
                descriptionTextarea.classList.add("error");
            }

            return (titleLength >= 3 && descriptionLength >= 3);
        }


        document.getElementById('add_author').addEventListener('click', function () {
            let authors = document.getElementById('authors');
            let newAuthor = createAuthorBlock(amount_authors++, "");
            authors.appendChild(newAuthor);
        });


        document.addEventListener('click', function (event) {
            if (event.target && event.target.classList.contains('add_author_to_fits')) {

                let authorsButtonId = event.target.id;
                let authorsId = authorsButtonId.replace("_button", "");
                let authors = document.getElementById(authorsId);
                let id = authorsId.replace("_form_authors", "")
                let newAuthor = createAuthorBlock(amount_authors, `fits_models-${id}-`);
                authors.appendChild(newAuthor);

            }
        });

        function show_loading() {
            document.getElementById("upload_button").style.display = "none";
            document.getElementById("loading").style.display = "block";
        }

        function hide_loading() {
            document.getElementById("upload_button").style.display = "block";
            document.getElementById("loading").style.display = "none";
        }

        function clean_upload_errors() {
            let upload_error = document.getElementById("upload_error");
            upload_error.innerHTML = "";
            upload_error.style.display = 'none';
        }

        function write_upload_error(error_message) {
            let upload_error = document.getElementById("upload_error");
            let alert = document.createElement('p');
            alert.style.margin = '0';
            alert.style.padding = '0';
            alert.textContent = 'Upload error: ' + error_message;
            upload_error.appendChild(alert);
            upload_error.style.display = 'block';
        }

        window.onload = function () {

            test_fakenodo_connection();

            document.getElementById('upload_button').addEventListener('click', function () {

                clean_upload_errors();
                show_loading();

                // check title and description
                let check = check_title_and_description();

                if (check) {
                    // process data form
                    const formData = {};

                    ["basic_info_form", "uploaded_models_form"].forEach((formId) => {
                        const form = document.getElementById(formId);
                        const inputs = form.querySelectorAll('input, select, textarea');
                        inputs.forEach(input => {
                            if (input.name) {
                                formData[input.name] = formData[input.name] || [];
                                formData[input.name].push(input.value);
                            }
                        });
                    });

                    let formDataJson = JSON.stringify(formData);
                    console.log(formDataJson);

                    const csrfToken = document.getElementById('csrf_token').value;
                    const formUploadData = new FormData();
                    formUploadData.append('csrf_token', csrfToken);

                    for (let key in formData) {
                        if (formData.hasOwnProperty(key)) {
                            formUploadData.set(key, formData[key]);
                        }
                    }

                    let checked_orcid = true;
                    if (Array.isArray(formData.author_orcid)) {
                        for (let orcid of formData.author_orcid) {
                            orcid = orcid.trim();
                            if (orcid !== '' && !isValidOrcid(orcid)) {
                                hide_loading();
                                write_upload_error("ORCID value does not conform to valid format: " + orcid);
                                checked_orcid = false;
                                break;
                            }
                        }
                    }


                    let checked_name = true;
                    if (Array.isArray(formData.author_name)) {
                        for (let name of formData.author_name) {
                            name = name.trim();
                            if (name === '') {
                                hide_loading();
                                write_upload_error("The author's name cannot be empty");
                                checked_name = false;
                                break;
                            }
                        }
                    }


                    if (checked_orcid && checked_name) {
                        fetch('/dataset/upload', {
                            method: 'POST',
                            body: formUploadData
                        })
                            .then(response => {
                                if (response.ok) {
                                    console.log('Dataset sent successfully');
                                    response.json().then(data => {
                                        console.log(data.message);
                                        window.location.href = "/dataset/list";
                                    });
                                } else {
                                    response.json().then(data => {
                                        console.error('Error: ' + data.message);
                                        hide_loading();

                                        write_upload_error(data.message);

                                    });
                                }
                            })
                            .catch(error => {
                                console.error('Error in POST request:', error);
                            });
                    }


                } else {
                    hide_loading();
                }


            });
        };


        function isValidOrcid(orcid) {
            let orcidRegex = /^\d{4}-\d{4}-\d{4}-\d{4}$/;
            return orcidRegex.test(orcid);
        }

        // Make this globally accessible
        function addFitsListItem(filename, dropzoneFile, isFromZip) {
            let fileList = document.getElementById('file-list');
            console.log("File uploaded entry: ", filename);
            let listItem = document.createElement('li');
            let h4Element = document.createElement('h4');
            h4Element.textContent = filename;
            listItem.appendChild(h4Element);

            // generate incremental id for form
            let formUniqueId = generateIncrementalId();

            /* FORM BUTTON */
            let formButton = document.createElement('button');
            formButton.innerHTML = 'Show info';
            formButton.classList.add('info-button', 'btn', 'btn-outline-secondary', "btn-sm");
            formButton.style.borderRadius = '5px';
            formButton.id = formUniqueId + "_button";

            // formContainer will be created below
            formButton.addEventListener('click', function () {
                if (formContainer.style.display === "none") {
                    formContainer.style.display = "block";
                    formButton.innerHTML = 'Hide info';
                } else {
                    formContainer.style.display = "none";
                    formButton.innerHTML = 'Add info';
                }
            });

            // append space
            let space = document.createTextNode(" ");
            listItem.appendChild(space);

            /* REMOVE BUTTON */
            let removeButton = document.createElement('button');
            removeButton.innerHTML = 'Delete model';
            removeButton.classList.add("remove-button", "btn", "btn-outline-danger", "btn-sm", "remove-button");
            removeButton.style.borderRadius = '5px';

            // append space
            space = document.createTextNode(" ");
            listItem.appendChild(space);

            removeButton.addEventListener('click', function () {
                // remove the UI list item
                fileList.removeChild(listItem);

                // only remove the Dropzone file when this corresponds to the actual uploaded dropzone file (single FITS upload)
                // NOT SURE OF THIS ONE, MAYBE ALWAYS REMOVE?
                if (!isFromZip) {
                    try {
                        dropzone.removeFile(dropzoneFile);
                    } catch (e) {
                        console.debug('Could not remove dropzone file:', e);
                    }
                }

                // Ajax request to delete that filename on the server
                let xhr = new XMLHttpRequest();
                xhr.open('POST', '/dataset/file/delete', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function () {
                    if (xhr.status === 200) {
                        console.log('Deleted file from server');

                        if (dropzone.files.length === 0) {
                            document.getElementById("upload_dataset").style.display = "none";
                            clean_upload_errors();
                        }

                    }
                };
                xhr.send(JSON.stringify({file: filename}));
            });

            /* APPEND BUTTONS */
            listItem.appendChild(formButton);
            listItem.appendChild(removeButton);

            /* FITS FORM */
            let formContainer = document.createElement('div');
            formContainer.id = formUniqueId + "_form";
            formContainer.classList.add('fits_form', "mt-3");
            formContainer.style.display = "none";

            formContainer.innerHTML = `
                <div class="row">
                    <input type="hidden" value="${filename}" name="fits_models-${formUniqueId}-fits_filename">
                    <div class="col-12">
                        <div class="row">
                            <div class="col-12">
                                <div class="mb-3">
                                    <label class="form-label">Title</label>
                                    <input type="text" class="form-control" name="fits_models-${formUniqueId}-title">
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="mb-3">
                                    <label class="form-label">Description</label>
                                    <textarea rows="4" class="form-control" name="fits_models-${formUniqueId}-desc"></textarea>
                                </div>
                            </div>
                            <div class="col-lg-6 col-12">
                                <div class="mb-3">
                                    <label class="form-label" for="publication_type">Publication type</label>
                                    <select class="form-control" name="fits_models-${formUniqueId}-publication_type">
                                        <option value="none">None</option>
                                        <option value="annotationcollection">Annotation Collection</option>
                                        <option value="book">Book</option>
                                        <option value="section">Book Section</option>
                                        <option value="conferencepaper">Conference Paper</option>
                                        <option value="datamanagementplan">Data Management Plan</option>
                                        <option value="article">Journal Article</option>
                                        <option value="patent">Patent</option>
                                        <option value="preprint">Preprint</option>
                                        <option value="deliverable">Project Deliverable</option>
                                        <option value="milestone">Project Milestone</option>
                                        <option value="proposal">Proposal</option>
                                        <option value="report">Report</option>
                                        <option value="softwaredocumentation">Software Documentation</option>
                                        <option value="taxonomictreatment">Taxonomic Treatment</option>
                                        <option value="technicalnote">Technical Note</option>
                                        <option value="thesis">Thesis</option>
                                        <option value="workingpaper">Working Paper</option>
                                        <option value="other">Other</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-lg-6 col-6">
                                <div class="mb-3">
                                    <label class="form-label" for="publication_doi">Publication DOI</label>
                                    <input class="form-control" name="fits_models-${formUniqueId}-publication_doi" type="text" value="">
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="mb-3">
                                    <label class="form-label">Tags (separated by commas)</label>
                                    <input type="text" class="form-control" name="fits_models-${formUniqueId}-tags">
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="mb-3">
                                    <label class="form-label">FITS version</label>
                                    <input type="text" class="form-control" name="fits_models-${formUniqueId}-fits_version">
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="mb-3">
                                    <label class="form-label">Authors</label>
                                    <div id="` + formContainer.id + `_authors">
                                    </div>
                                    <button type="button" class="add_author_to_fits btn btn-secondary" id="` + formContainer.id + `_authors_button">Add author</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                `;

            listItem.appendChild(formContainer);
            fileList.appendChild(listItem);
        }

        document.getElementById('github_fetch_btn').addEventListener('click', function() {
            const githubUrl = document.getElementById('github_url').value.trim();
            const githubError = document.getElementById('github_error');
            const github_fetch_btn = document.getElementById('github_fetch_btn');
            githubError.style.display = 'none';
            githubError.textContent = '';

            if (!githubUrl) {
                githubError.textContent = "Please enter a GitHub repository URL";
                githubError.style.display = 'block';
                return;
            }

            // Extract user/repo from URL
            const repoMatch = githubUrl.match(/github\.com\/([^\/]+)\/([^\/]+)(\/|$)/);
            if (!repoMatch) {
                githubError.textContent = "Invalid GitHub repository URL";
                githubError.style.display = 'block';
                return;
            }

            const user = repoMatch[1];
            const repo = repoMatch[2];

            github_fetch_btn.disabled = true;

            fetch(`/dataset/github/fetch?user=${user}&repo=${repo}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(response => response.json())
                .then(data => {
                    console.log(data)
                    if (data.error) {
                        githubError.textContent = data.error;
                        githubError.style.display = 'block';
                        return;
                    }

                    const filenames = data.filenames || [];
                    if (filenames.length === 0) {
                        githubError.textContent = "No FITS files found in the repository";
                        githubError.style.display = 'block';
                        return;
                    }

                    const fileList = document.getElementById('file-list');
                    fileList.innerHTML = ''; // Clear previous list

                    filenames.forEach(filename => {
                        addFitsListItem(filename, null, true); // null for dropzone file since it's GitHub
                    });

                    show_upload_dataset();
                })
                .catch(err => {
                    console.error(err);
                    githubError.textContent = "Error fetching from GitHub. Check the URL or repository permissions.";
                    githubError.style.display = 'block';
                })
                .finally(() => github_fetch_btn.disabled = false);
        });
