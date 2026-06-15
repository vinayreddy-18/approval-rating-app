document.addEventListener('DOMContentLoaded', () => {
    const cards = Array.from(document.querySelectorAll('.politician-card'));
    const chartCanvas = document.getElementById('vote-distribution-chart');

    const updateText = (selector, value) => {
        const el = document.querySelector(selector);
        if (el) {
            el.textContent = value;
        }
    };

    const refreshTopComparison = (comparison) => {
        const list = document.getElementById('top-ratings-list');
        const leaderBadge = document.getElementById('leader-badge-name');
        if (!list || !comparison) return;

        list.innerHTML = comparison.ratings.map((rating) => `
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

        updateText('#current-leader-name', comparison.leader_name || 'N/A');
        updateText('#current-leader-approval', `${comparison.ratings[0]?.approval ?? 0}%`);
        updateText('#comparison-lead-value', `${comparison.lead_display || '+0'}%`);
        updateText('#current-leader-lead', `${comparison.lead_display || '+0'}%`);
        if (leaderBadge) {
            leaderBadge.textContent = comparison.leader_name || 'N/A';
        }
    };

    const refreshPlatformStats = (platformStats) => {
        const stats = platformStats || {};
        updateText('#platform-total-votes', stats.total_votes_cast ?? 0);
        updateText('#platform-total-votes-secondary', stats.total_votes_cast ?? 0);
        updateText('#platform-last-vote-time', stats.last_vote_time || 'No votes yet');

        const breakdown = document.getElementById('platform-vote-breakdown');
        if (breakdown && stats.vote_counts) {
            breakdown.innerHTML = stats.vote_counts.map((entry) => `
                <div class="d-flex justify-content-between py-2 breakdown-row" data-name="${entry.name}" data-count="${entry.vote_count}">
                    <span>${entry.name}</span>
                    <span>${entry.vote_count}</span>
                </div>
            `).join('');
        }

        if (chartCanvas && stats.vote_counts) {
            const ctx = chartCanvas.getContext('2d');
            const labels = stats.vote_counts.map((entry) => entry.name);
            const values = stats.vote_counts.map((entry) => entry.vote_count);

            if (window.voteChart) {
                window.voteChart.destroy();
            }

            window.voteChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: ['#2dd4bf', '#60a5fa', '#f59e0b', '#f43f5e']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    };

    const updateCardStats = (card, stats) => {
        if (!card || !stats) return;

        const approval = card.querySelector('.approval');
        const neutral = card.querySelector('.neutral-count');
        const disapproval = card.querySelector('.disapproval');
        const totalVotes = card.querySelector('.total-votes');
        const netApproval = card.querySelector('.net-approval');
        const feedback = card.querySelector('.vote-feedback');
        const userVote = card.querySelector('.user-vote');
        const lastUpdated = card.querySelector('.last-updated');

        if (approval) approval.textContent = stats.approval;
        if (neutral) neutral.textContent = stats.neutral;
        if (disapproval) disapproval.textContent = stats.disapproval;
        if (totalVotes) totalVotes.textContent = stats.total_votes;
        if (netApproval) {
            netApproval.textContent = `${stats.net_approval >= 0 ? '+' : ''}${stats.net_approval}`;
            netApproval.className = `net-approval ${stats.net_approval >= 0 ? 'text-success' : 'text-danger'}`;
        }
        if (feedback) {
            feedback.textContent = 'Vote updated successfully.';
        }
        if (userVote) {
            if (stats.user_vote === 'approve') {
                userVote.textContent = '✓ Your Vote: Approve';
            } else if (stats.user_vote === 'neutral') {
                userVote.textContent = '✓ Your Vote: Neutral';
            } else if (stats.user_vote === 'disapprove') {
                userVote.textContent = '✓ Your Vote: Disapprove';
            } else {
                userVote.textContent = 'No vote yet';
            }
        }
        if (lastUpdated) {
            lastUpdated.textContent = 'Last Updated: Just now';
        }
    };

    const updateProgressBars = (card, stats) => {
        const approvalBar = card.querySelector('.approval-bar');
        const neutralBar = card.querySelector('.neutral-bar');
        const disapprovalBar = card.querySelector('.disapproval-bar');

        if (approvalBar) {
            approvalBar.style.width = `${stats.approval}%`;
            approvalBar.setAttribute('aria-valuenow', stats.approval);
        }
        if (neutralBar) {
            neutralBar.style.width = `${stats.neutral}%`;
            neutralBar.setAttribute('aria-valuenow', stats.neutral);
        }
        if (disapprovalBar) {
            disapprovalBar.style.width = `${stats.disapproval}%`;
            disapprovalBar.setAttribute('aria-valuenow', stats.disapproval);
        }
    };

    const handleVote = async (card, voteType) => {
        const politicianId = Number(card.dataset.id);
        const userUid = localStorage.getItem('firebase-uid');

        if (!userUid) {
            window.alert('Please sign in first.');
            return;
        }

        const response = await fetch('/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ politician_id: politicianId, vote_type: voteType, user_uid: userUid })
        });

        const data = await response.json();
        if (!response.ok) {
            window.alert(data.error || 'Vote failed.');
            return;
        }

        const voteCard = card;
        const currentStats = {
            approval: data.approval,
            neutral: data.neutral,
            disapproval: data.disapproval,
            total_votes: data.total_votes,
            net_approval: data.net_approval,
            user_vote: data.user_vote
        };

        updateCardStats(voteCard, currentStats);
        updateProgressBars(voteCard, currentStats);
        refreshTopComparison(data.comparison);
        refreshPlatformStats(data.platform_stats);
    };

    cards.forEach((card) => {
        card.querySelectorAll('.vote-btn').forEach((button) => {
            button.addEventListener('click', () => handleVote(card, button.classList.contains('approve') ? 'approve' : button.classList.contains('neutral') ? 'neutral' : 'disapprove'));
        });
    });

    refreshPlatformStats({
        total_votes_cast: document.getElementById('platform-total-votes')?.textContent || 0,
        last_vote_time: document.getElementById('platform-last-vote-time')?.textContent || 'No votes yet',
        vote_counts: Array.from(document.querySelectorAll('#platform-vote-breakdown .breakdown-row')).map((row) => ({
            name: row.dataset.name,
            vote_count: Number(row.dataset.count || 0)
        }))
    });
});
