document.addEventListener('DOMContentLoaded', () => {
    const output = document.getElementById('output');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('resumeFile');
    const fileNameDisplay = document.getElementById('fileName');
    const jobRoleSelect = document.getElementById('jobRole');
    const uploadForm = document.getElementById('uploadForm');
    const resultsArea = document.getElementById('resultsArea');
    const analyzeBtn = document.querySelector('.analyze-btn');
    const btnText = analyzeBtn.querySelector('span');
    const btnLoader = document.getElementById('btnLoader');

    // Job Search Elements
    const searchJobsBtn = document.getElementById('searchJobsBtn');
    const jobLocationInput = document.getElementById('jobLocation');
    const jobResultsGrid = document.getElementById('jobResults');
    const jobLoader = document.getElementById('jobLoader');

    // State
    let currentResumeText = "";
    let currentJobRole = "";

    // File Upload Handling
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateFileDisplay();
        }
    });

    fileInput.addEventListener('change', updateFileDisplay);

    function updateFileDisplay() {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
            dropZone.style.borderColor = 'var(--success)';
            document.querySelector('.upload-text').style.display = 'none';
        }
    }

    // Form Submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (fileInput.files.length === 0 || jobRoleSelect.value === "") {
            alert("Please select a job role and upload a resume.");
            return;
        }

        // UI Loading State
        setLoading(true);

        const formData = new FormData();
        formData.append('resume', fileInput.files[0]);
        formData.append('job_role', jobRoleSelect.value);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Analysis failed");
            }

            const data = await response.json();

            // Update State
            currentResumeText = data.resume_text || "";
            currentJobRole = data.job_role || jobRoleSelect.value;

            displayResults(data);

        } catch (error) {
            console.error(error);
            alert(error.message);
        } finally {
            setLoading(false);
        }
    });

    // Job Search Handling
    searchJobsBtn.addEventListener('click', async () => {
        if (!currentJobRole) {
            alert("Please analyze a resume first to set the target job role.");
            return;
        }

        jobLoader.classList.remove('hidden');
        jobResultsGrid.innerHTML = ''; // Clear previous
        searchJobsBtn.disabled = true;

        try {
            const response = await fetch('/search_jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    job_role: currentJobRole,
                    location: jobLocationInput.value,
                    resume_text: currentResumeText
                })
            });

            if (!response.ok) {
                throw new Error("Failed to fetch jobs");
            }

            const data = await response.json();
            displayJobResults(data.jobs);

        } catch (error) {
            console.error(error);
            jobResultsGrid.innerHTML = `<p style="color: #ef4444; text-align: center;">Error searching jobs: ${error.message}</p>`;
        } finally {
            jobLoader.classList.add('hidden');
            searchJobsBtn.disabled = false;
        }
    });

    function displayJobResults(jobs) {
        if (!jobs || jobs.length === 0) {
            jobResultsGrid.innerHTML = '<p style="text-align: center; color: rgba(255,255,255,0.6);">No matching jobs found. Try a different location or role.</p>';
            return;
        }

        jobs.forEach(job => {
            const card = document.createElement('div');
            card.className = 'job-card';

            const matchColor = job.match_score >= 70 ? '#22c55e' : (job.match_score >= 50 ? '#f59e0b' : '#ef4444');

            card.innerHTML = `
                <div class="job-header">
                    <div>
                        <div class="job-title">${job.title}</div>
                        <div class="job-company">${job.company}</div>
                    </div>
                    <div class="job-match-badge" style="background: ${matchColor};">
                        ${job.match_score}% Match
                    </div>
                </div>
                <div class="job-location"><i class="fas fa-map-marker-alt"></i> ${job.location}</div>
                <div class="job-desc">${job.description_snippet}</div>
                <a href="${job.job_url}" target="_blank" class="apply-btn">Apply Now <i class="fas fa-external-link-alt"></i></a>
            `;
            jobResultsGrid.appendChild(card);
        });
    }

    function setLoading(isLoading) {
        if (isLoading) {
            analyzeBtn.disabled = true;
            btnText.style.visibility = 'hidden';
            btnLoader.style.display = 'block';
            resultsArea.classList.add('hidden');
        } else {
            analyzeBtn.disabled = false;
            btnLoader.style.display = 'none';
            btnText.style.visibility = 'visible';
        }
    }

    function displayResults(data) {
        resultsArea.classList.remove('hidden');

        // Update Chart
        const percentage = data.match_percentage;
        const circle = document.querySelector('.circle');
        const percentageText = document.querySelector('.percentage');

        circle.setAttribute('stroke-dasharray', `${percentage}, 100`);

        if (percentage < 40) {
            circle.style.stroke = '#ef4444';
        } else if (percentage < 70) {
            circle.style.stroke = '#f59e0b';
        } else {
            circle.style.stroke = '#22c55e';
        }

        let current = 0;
        const timer = setInterval(() => {
            current += 1;
            percentageText.textContent = `${current}%`;
            if (current >= Math.floor(percentage)) {
                clearInterval(timer);
                percentageText.textContent = `${percentage}%`;
            }
        }, 10);

        // Comments
        const comments = document.getElementById('matchComment');
        if (percentage > 80) comments.textContent = "Excellent match! You are a strong candidate.";
        else if (percentage > 50) comments.textContent = "Good match, but some key skills are missing.";
        else comments.textContent = "Low match. Consider upskilling in the missing areas.";

        // Populate Lists
        const missingList = document.getElementById('missingSkillsList');
        const matchedList = document.getElementById('matchedSkillsList');

        missingList.innerHTML = '';
        matchedList.innerHTML = '';

        if (data.missing_skills.length === 0) {
            missingList.innerHTML = '<li>None! You have all required skills.</li>';
        } else {
            data.missing_skills.forEach(item => {
                const li = document.createElement('li');
                li.className = 'skill-item-missing';
                li.innerHTML = `
                    <span>${item.skill}</span>
                    <a href="${item.link}" target="_blank" class="learn-btn" title="Learn this skill">
                        <i class="fas fa-external-link-alt"></i> Learn
                    </a>
                `;
                missingList.appendChild(li);
            });
        }

        if (data.matched_skills.length === 0) {
            matchedList.innerHTML = '<li>No specific skills matched.</li>';
        } else {
            data.matched_skills.forEach(skill => {
                const li = document.createElement('li');
                li.textContent = skill;
                matchedList.appendChild(li);
            });
        }

        // Candidate Info
        const candidateInfoDiv = document.getElementById('candidateInfo');
        if (candidateInfoDiv && data.candidate_info) {
            candidateInfoDiv.innerHTML = `
                <div class="info-item"><i class="fas fa-envelope"></i> ${data.candidate_info.email}</div>
                <div class="info-item"><i class="fas fa-phone"></i> ${data.candidate_info.phone}</div>
            `;
        }

        // Smart Tips
        const tipsList = document.getElementById('tipsList');
        if (tipsList && data.tips) {
            tipsList.innerHTML = '';
            data.tips.forEach(tip => {
                const li = document.createElement('li');
                li.textContent = tip;
                tipsList.appendChild(li);
            });
        }

        // Recommendations
        const recList = document.getElementById('recommendationList');
        recList.innerHTML = '';

        if (data.recommendations && data.recommendations.length > 0) {
            data.recommendations.forEach(rec => {
                const card = document.createElement('div');
                card.className = 'rec-card';
                card.innerHTML = `
                    <span class="rec-role">${rec.role}</span>
                    <div class="rec-percentage">${rec.percentage}%</div>
                `;
                recList.appendChild(card);
            });
        } else {
            recList.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.5);">No specific recommendations found.</p>';
        }

        // Scroll to results
        resultsArea.scrollIntoView({ behavior: 'smooth' });
    }
});
