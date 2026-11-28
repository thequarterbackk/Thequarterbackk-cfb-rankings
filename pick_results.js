const weeklyPickResults = [
  {
    date: 'Sept. 12',
    right: 'Toledo, Arkansas State, USC, Colorado, Nebraska, Washington, SMU, Texas Tech, Western Michigan, Penn State, UMass, Central Michigan, Wyoming, San Jose State, Colorado State, Virginia Tech, Kansas State, Michigan State, Tulsa',
    wrong: 'Oregon',
  },
  {
    date: 'Sept. 19',
    right: 'USC, North Dakota State, Utah, Appalachian State, Penn State −40.5, Cincinnati, Michigan −34.5, Georgia, Duke, Iowa State, Alabama, James Madison, UCLA, Kansas State, Arizona',
    wrong: 'Coastal Carolina, Indiana −44.5, Texas A&M, North Texas, North Carolina',
  },
  {
    date: 'Sept. 26',
    right: 'South Florida, Notre Dame, UMass, James Madison, Georgia State, Florida Atlantic, Louisiana, Texas Tech −13.5, New Mexico, Miami (FL) −21.5, Virginia Tech, Fresno State, Houston, SMU',
    wrong: 'Tulsa, USC, Troy, Appalachian State, Penn State, UConn',
  },
  {
    date: 'Oct. 3',
    right: 'Indiana, New Mexico, Memphis, North Dakota State, Toledo, South Alabama, Texas Tech, Nebraska, Notre Dame, UTSA, Boise State, Georgia State, Fresno State, James Madison, Miami (FL), Georgia',
    wrong: 'South Florida, UMass, Miami (OH), Coastal Carolina',
  },
  {
    date: 'Oct. 10',
    right: 'Notre Dame −18.5, James Madison, Northwestern −14.5, North Texas, Air Force, Ohio State −12.5, Tennessee, Utah, Eastern Michigan, Western Michigan',
    wrong: 'Duke, Pittsburgh, North Dakota State, Virginia Tech, Toledo, Appalachian State, UMass, Minnesota, Texas, Florida',
  },
  {
    date: 'Oct. 17',
    right: 'Oregon State, Miami (FL), South Florida, Texas Tech, New Mexico, Miami (OH), Houston, Virginia Tech, LSU, Utah, James Madison, Ohio, UCLA, UTSA',
    wrong: 'Georgia, Temple, South Dakota State, Pittsburgh, Texas, Bowling Green',
  },
  {
    date: 'Oct. 24',
    right: 'Northwestern, Kentucky, UCLA, Miami (FL), Oklahoma State, Texas State, Alabama, Ohio, Louisiana Tech, Ball State, SMU, Florida Atlantic, Arizona, Buffalo, Boise State, Indiana, New Mexico',
    wrong: 'Troy, TCU, North Carolina',
  },
  {
    date: 'Oct. 31',
    right: 'Indiana, Louisville, North Dakota State, UNLV, Notre Dame, UCLA, Liberty, Western Michigan, BYU, Pittsburgh, Wake Forest, Boise State, Texas, Ole Miss, South Florida, Duke, New Mexico, Coastal Carolina, NC State',
    wrong: 'Nebraska',
  },
  {
    date: 'Nov. 7',
    right: 'North Texas, Wisconsin, Jacksonville State, Houston, San Jose State, UAB, Liberty, Texas Tech, Baylor, Georgia Southern, Boise State, Utah, Louisiana, Louisville',
    wrong: 'Arkansas State, Coastal Carolina, Purdue, Ohio State, Mississippi State, Florida',
  },
  {
    date: 'Nov. 14',
    right: 'Notre Dame, Liberty, Louisiana Tech, Iowa, Oregon, Alabama, Georgia, Virginia, Miami (FL), TCU, Air Force, Boise State, Penn State, Indiana, Texas State, Tulsa',
    wrong: 'New Mexico, Clemson, Virginia Tech, UCF',
  },
  {
    date: 'Nov. 21',
    right: 'North Dakota State, Miami (FL), Tulsa, Liberty, Fresno State, Notre Dame, Wake Forest, Louisiana Tech, Texas, UConn, Appalachian State, Florida, USC, Jacksonville State, Oregon State, Texas State, BYU',
    wrong: 'Boise State, Penn State, Ohio State',
  },
];

function pickCount(picks) {
  return picks ? picks.split(', ').length : 0;
}

function pickAccuracy(right, wrong) {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(right + wrong ? right / (right + wrong) : 0);
}

function renderPickResults() {
  const body = document.getElementById('pickResultsBody');
  let totalRight = 0;
  let totalWrong = 0;

  weeklyPickResults.forEach(({ date, right, wrong }, index) => {
    const week = index + 1;
    const wins = pickCount(right);
    const losses = pickCount(wrong);
    totalRight += wins;
    totalWrong += losses;

    const row = body.insertRow();
    const weekCell = document.createElement('th');
    weekCell.scope = 'row';
    row.append(weekCell);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'pick-week-toggle';
    button.textContent = `Week ${week}`;
    button.setAttribute('aria-expanded', 'false');
    weekCell.append(button);

    for (const value of [date, wins, losses, pickAccuracy(wins, losses)]) {
      row.insertCell().textContent = value;
    }

    const detail = body.insertRow();
    detail.id = `pick-results-week-${week}`;
    detail.hidden = true;
    button.setAttribute('aria-controls', detail.id);
    const detailCell = detail.insertCell();
    detailCell.colSpan = 5;
    detailCell.className = 'pick-week-detail';

    for (const [label, picks] of [['Right', right], ['Wrong', wrong]]) {
      const line = document.createElement('p');
      const heading = document.createElement('strong');
      heading.textContent = label;
      line.append(heading, ` · ${picks || 'None'}`);
      detailCell.append(line);
    }

    button.addEventListener('click', () => {
      detail.hidden = !detail.hidden;
      button.setAttribute('aria-expanded', String(!detail.hidden));
    });
  });

  document.getElementById('pickOverallRecord').textContent =
    `Overall record · ${totalRight}–${totalWrong} (${pickAccuracy(totalRight, totalWrong)})`;
}

renderPickResults();
