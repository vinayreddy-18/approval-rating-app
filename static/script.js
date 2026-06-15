let voteDistributionChart = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('Approval Rating App loaded.');

    attachVoteListeners();
    refreshTopComparison();
    refreshPlatformStats();
    renderVoteDistributionChart();

    const uid = localStorage.getItem('uid');
    if (uid) {
        // Frontend rendering logic: request the latest user-vote state for this signed-in user.
        refreshUserVotes(uid);
    }
});

function attachVoteListeners() {
    const voteButtons = document.querySelectorAll('.vote-btn');

    voteButtons.forEach((button) => {
        button.addEventListener('click', async (event) => {
            const voteType = getVoteType(event.currentTarget);
            const card = event.currentTarget.closest('.politician-card');

            if (!card || !voteType) {
                console.error('Missing politician card or vote type');
                return;
            }

            const politicianId = parseInt(card.dataset.id, 10);
            if (Number.isNaN(politicianId)) {
                console.error('Invalid politician id', card.dataset.id);
                return;
            }

            const userUid = localStorage.getItem('uid');
            if (!userUid) {
                alert('Please sign in with Google before voting.');
                return;
            }

            const previousApproval = parseInt(card.querySelector('.approval').textContent, 10) || 0;

            console.log('Sending vote', { politicianId, voteType, userUid });

            try {
                const response = await fetch('/vote', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user_uid: userUid,
                        politician_id: politicianId,
                        vote_type: voteType
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    console.error('Vote request failed', response.status, errorData);
                    alert(errorData.error || 'Vote request failed. Please try again.');
                    return;
                }

                const data = await response.json();
                console.log('Vote response', data);

                updateCardStats(card, data, previousApproval);
                updateDisplayedVote(card, data.user_vote);
                refreshTopComparison(data.comparison);
                refreshPlatformStats(data.platform_stats);
            } catch (error) {
                console.error('Error sending vote', error);
                alert('Error sending vote. Please try again.');
            }
        });
    });
}

function getVoteType(button) {
    if (button.classList.contains('approve')) {
        return 'approve';
    }
    if (button.classList.contains('neutral')) {
        return 'neutral';
    }
    if (button.classList.contains('disapprove')) {
        return 'disapprove';
    }
    return null;
}

function formatUserVoteText(voteType) {
    switch (voteType) {
        case 'approve':
            return 'You voted: 👍 Approve';
        case 'neutral':
            return 'You voted: 😐 Neutral';
        case 'disapprove':
            return 'You voted: 👎 Disapprove';
        default:
            return 'No vote yet';
    }
}

function updateDisplayedVote(card, voteType) {
    const voteElement = card.querySelector('.user-vote');
    if (voteElement) {
        voteElement.textContent = formatUserVoteText(voteType);
    }
}

async function refreshUserVotes(uid) {
    try {
        const response = await fetch(`/?uid=${encodeURIComponent(uid)}&format=json`, {
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        const politicians = Array.isArray(data.politicians) ? data.politicians : [];

        politicians.forEach((politician) => {
            const card = document.querySelector(`.politician-card[data-id="${politician.id}"]`);
            if (!card) {
                return;
            }
            updateDisplayedVote(card, politician.user_vote);
        });
    } catch (error) {
        console.error('Unable to refresh user votes', error);
    }
}

function updateCardStats(card, data, previousApproval) {
    if (!data || typeof data.approval !== 'number') {
        console.error('Invalid vote response data', data);
        return;
    }

    const approvalBar = card.querySelector('.approval-bar');
    const neutralBar = card.querySelector('.neutral-bar');
    const disapprovalBar = card.querySelector('.disapproval-bar');

    approvalBar.style.width = `${data.approval}%`;
    approvalBar.innerText = `${data.approval}%`;
    approvalBar.setAttribute('aria-valuenow', data.approval);

    neutralBar.style.width = `${data.neutral}%`;
    neutralBar.innerText = `${data.neutral}%`;
    neutralBar.setAttribute('aria-valuenow', data.neutral);

    disapprovalBar.style.width = `${data.disapproval}%`;
    disapprovalBar.innerText = `${data.disapproval}%`;
    disapprovalBar.setAttribute('aria-valuenow', data.disapproval);

    card.querySelector('.approval').innerText = data.approval;
    card.querySelector('.neutral-count').innerText = data.neutral;
    card.querySelector('.disapproval').innerText = data.disapproval;
    card.querySelector('.total-votes').innerText = data.total_votes;

    const netApproval = data.net_approval;
    const netElement = card.querySelector('.net-approval');
    netElement.innerText = `${netApproval >= 0 ? '+' : ''}${netApproval}`;
    netElement.classList.toggle('text-success', netApproval >= 0);
    netElement.classList.toggle('text-danger', netApproval < 0);

    const feedbackElement = card.querySelector('.vote-feedback');
    if (feedbackElement) {
        feedbackElement.textContent = `Approval changed: ${previousApproval}% → ${data.approval}%`;
    }
}

function refreshTopComparison(comparison) {
    const leaderNameElement = document.querySelector('#current-leader-name');
    const leaderApprovalElement = document.querySelector('#current-leader-approval');
    const leaderLeadElement = document.querySelector('#current-leader-lead');
    const comparisonLeadElement = document.querySelector('#comparison-lead-value');
    const topRatingsList = document.querySelector('#top-ratings-list');

    if (comparison && comparison.ratings) {
        if (leaderNameElement) {
            leaderNameElement.innerText = comparison.leader_name;
        }
        if (leaderApprovalElement) {
            leaderApprovalElement.innerText = `${comparison.ratings[0]?.approval ?? 0}%`;
        }
        if (leaderLeadElement) {
            leaderLeadElement.innerText = `${comparison.lead_display}%`;
        }
        if (comparisonLeadElement) {
            comparisonLeadElement.innerText = `${comparison.lead_display}%`;
        }
        if (topRatingsList) {
            topRatingsList.innerHTML = comparison.ratings.map((rating) => `
                <div class="comparison-row">
                    <div class="d-flex justify-content-between mb-2">
                        <span class="comparison-name">${rating.name}</span>
                        <span class="comparison-score">${rating.approval}%</span>
                    </div>
                    <div class="progress comparison-progress">
                        <div class="progress-bar bg-success" role="progressbar" style="width: ${rating.approval}%;" aria-valuenow="${rating.approval}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>
            `).join('');
        }
        return;
    }

    const cards = document.querySelectorAll('.politician-card');
    const ratings = Array.from(cards).map((card) => {
        const name = card.querySelector('.card-title').innerText.trim();
        const approval = parseInt(card.querySelector('.approval-bar').getAttribute('aria-valuenow'), 10) || 0;
        return { name, approval };
    });

    if (ratings.length === 0) {
        return;
    }

    ratings.sort((a, b) => b.approval - a.approval);
    const leader = ratings[0];
    const secondApproval = ratings[1] ? ratings[1].approval : 0;
    const lead = leader.approval - secondApproval;

    if (leaderNameElement) {
        leaderNameElement.innerText = leader.name;
    }
    if (leaderApprovalElement) {
        leaderApprovalElement.innerText = `${leader.approval}%`;
    }
    if (leaderLeadElement) {
        leaderLeadElement.innerText = `${lead >= 0 ? '+' : ''}${lead}%`;
    }
    if (comparisonLeadElement) {
        comparisonLeadElement.innerText = `${lead >= 0 ? '+' : ''}${lead}%`;
    }
    if (topRatingsList) {
        topRatingsList.innerHTML = ratings.map((rating) => `
            <div class="comparison-row">
                <div class="d-flex justify-content-between mb-2">
                    <span class="comparison-name">${rating.name}</span>
                    <span class="comparison-score">${rating.approval}%</span>
                </div>
                <div class="progress comparison-progress">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${rating.approval}%;" aria-valuenow="${rating.approval}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        `).join('');
    }
}

function refreshPlatformStats(platformStats) {
    const totalVotesElement = document.querySelector('#platform-total-votes');
    const totalVotesSecondaryElement = document.querySelector('#platform-total-votes-secondary');
    const lastVoteTimeElement = document.querySelector('#platform-last-vote-time');
    const voteBreakdownElement = document.querySelector('#platform-vote-breakdown');

    if (platformStats) {
        if (totalVotesElement) {
            totalVotesElement.innerText = platformStats.total_votes_cast;
        }
        if (totalVotesSecondaryElement) {
            totalVotesSecondaryElement.innerText = platformStats.total_votes_cast;
        }
        if (lastVoteTimeElement) {
            lastVoteTimeElement.innerText = platformStats.last_vote_time;
        }
        if (voteBreakdownElement && Array.isArray(platformStats.vote_counts)) {
            voteBreakdownElement.innerHTML = platformStats.vote_counts.map((entry) => `
                <div class="d-flex justify-content-between py-2 breakdown-row" data-name="${entry.name}" data-count="${entry.vote_count}">
                    <span>${entry.name}</span>
                    <span>${entry.vote_count}</span>
                </div>
            `).join('');
        }
    }

    renderVoteDistributionChart();
}

function renderVoteDistributionChart() {
    const canvas = document.querySelector('#vote-distribution-chart');
    if (!canvas || typeof Chart === 'undefined') {
        return;
    }

    const breakdownRows = Array.from(document.querySelectorAll('#platform-vote-breakdown .breakdown-row'));
    const labels = breakdownRows.map((row) => row.dataset.name || 'Unknown');
    const values = breakdownRows.map((row) => parseInt(row.dataset.count, 10) || 0);

    if (voteDistributionChart) {
        voteDistributionChart.data.labels = labels;
        voteDistributionChart.data.datasets[0].data = values;
        voteDistributionChart.update();
        return;
    }

    voteDistributionChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ['#22c55e', '#38bdf8', '#f59e0b', '#ef4444', '#8b5cf6'],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#e2e8f0'
                    }
                }
            }
        }
    });
}
