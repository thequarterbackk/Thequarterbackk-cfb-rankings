let cfpRequest;

function initCfpComparison() {
  if (cfpRequest) return;
  const status = document.getElementById('cfpStatus');
  status.textContent = 'Loading CFP comparison…';
  cfpRequest = fetch('cfp_comparison.json', {cache: 'no-cache'})
    .then(response => {
      if (!response.ok) throw new Error('CFP comparison data could not load');
      return response.json();
    })
    .then(setupCfpComparison)
    .catch(error => {
      status.textContent = 'CFP comparison is temporarily unavailable. Reopen this tab to retry.';
      cfpRequest = null;
      console.error(error);
    });
}

function setupCfpComparison({polls, teams, source}) {
  const element = id => document.getElementById(id);
  const pollSelect = element('cfpPoll');
  const conferenceSelect = element('cfpConference');
  const scopeSelect = element('cfpScope');
  const sortSelect = element('cfpSort');
  const dateLabel = date => new Date(date + 'T12:00:00Z').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'
  });
  const conferences = [...new Set(Object.values(teams))].sort();
  const signed = value => value > 0 ? '+' + value : String(value);
  const gapClass = value => value > 0 ? 'move-up' : value < 0 ? 'move-down' : 'move-flat';

  pollSelect.replaceChildren(...polls.map(poll => new Option(dateLabel(poll.released), poll.released)));
  conferenceSelect.replaceChildren(new Option('All conferences', ''),
    ...conferences.map(conference => new Option(conference, conference)));
  element('cfpSource').href = source;

  function render() {
    const selected = polls.find(poll => poll.released === pollSelect.value);
    const official = new Map(selected.cfp.map((team, index) => [team, index + 1]));
    const model = new Map(selected.model.map(row => [row.team, row]));
    const modelTop25 = selected.model.filter(row => row.rank <= 25);
    const comparison = [...new Set([...selected.cfp, ...modelTop25.map(row => row.team)])]
      .map(team => {
        const cfpRank = official.get(team);
        const modelRank = model.get(team)?.rank;
        return {
          team, cfpRank, modelRank, conference: teams[team], record: model.get(team)?.record,
          gap: cfpRank && modelRank ? modelRank - cfpRank : null
        };
      });
    const shared25 = modelTop25.filter(row => official.has(row.team)).length;
    const shared10 = modelTop25.filter(row => row.rank <= 10 && official.get(row.team) <= 10).length;
    const gaps = comparison.filter(row => row.gap !== null);
    const largestShift = [...gaps].sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap))[0];
    const stats = [
      ['Top 25 overlap', shared25 + ' of 25'],
      ['Top 10 overlap', shared10 + ' of 10'],
      ['Largest measured gap', largestShift ? largestShift.team + ' (' + signed(largestShift.gap) + ')' : '—']
    ];
    element('cfpCutoff').textContent = 'Games through ' + dateLabel(selected.through);
    element('cfpSummary').innerHTML = stats.map(([label, value]) =>
      `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('');

    const scopeRules = {
      either: () => true,
      cfp: row => Boolean(row.cfpRank),
      model: row => row.modelRank <= 25,
      'cfp-only': row => row.cfpRank && !(row.modelRank <= 25),
      'model-only': row => row.modelRank <= 25 && !row.cfpRank
    };
    const order = {
      cfp: row => row.cfpRank ?? Infinity,
      model: row => row.modelRank ?? Infinity,
      gap: row => row.gap === null ? Infinity : -Math.abs(row.gap),
      higher: row => row.gap === null ? Infinity : -row.gap,
      lower: row => row.gap ?? Infinity
    }[sortSelect.value];
    const rows = comparison
      .filter(row => !conferenceSelect.value || row.conference === conferenceSelect.value)
      .filter(scopeRules[scopeSelect.value])
      .sort((a, b) => order(a) - order(b) || (a.modelRank ?? Infinity) - (b.modelRank ?? Infinity)
        || a.team.localeCompare(b.team));
    element('cfpTeams').innerHTML = rows.map(row => `<tr>
      <td><strong>${esc(row.team)}</strong></td><td>${esc(row.conference)}</td><td>${esc(row.record ?? '—')}</td>
      <td>${row.modelRank ? '#' + row.modelRank : 'NR'}</td><td>${row.cfpRank ? '#' + row.cfpRank : 'NR'}</td>
      <td class="cfp-gap ${gapClass(row.gap)}">${row.gap === null ? '—' : signed(row.gap)}</td>
    </tr>`).join('') || '<tr><td colspan="6">No teams match these filters.</td></tr>';

    const history = polls.filter(poll => poll.released <= selected.released);
    element('cfpHistoryHeading').textContent = 'Total across ' + history.length + (history.length === 1 ? ' release' : ' releases');
    element('cfpConferences').innerHTML = conferences.map(conference => {
      const modelCount = modelTop25.filter(row => teams[row.team] === conference).length;
      const cfpCount = selected.cfp.filter(team => teams[team] === conference).length;
      const total = history.reduce((sum, poll) => sum
        + poll.cfp.filter(team => teams[team] === conference).length
        - poll.model.filter(row => row.rank <= 25 && teams[row.team] === conference).length, 0);
      return {conference, modelCount, cfpCount, difference: cfpCount - modelCount, total};
    }).sort((a, b) => b.difference - a.difference || b.total - a.total || a.conference.localeCompare(b.conference))
      .map(row => `<tr>
        <td><strong>${esc(row.conference)}</strong></td><td>${row.modelCount}</td><td>${row.cfpCount}</td>
        <td class="cfp-gap ${gapClass(row.difference)}">${signed(row.difference)}</td>
        <td class="cfp-gap ${gapClass(row.total)}">${signed(row.total)}</td>
      </tr>`).join('');
  }

  render();
  for (const select of [pollSelect, conferenceSelect, scopeSelect, sortSelect]) {
    select.addEventListener('change', render);
  }
  element('cfpStatus').hidden = true;
  element('cfpContent').hidden = false;
}
