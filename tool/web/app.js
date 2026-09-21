const tableBody = document.querySelector('#fitment-table tbody');
const template = document.querySelector('#fitment-row-template');
const statusNode = document.querySelector('#app-status');
const validationNode = document.querySelector('#validation-message');
const resultsSection = document.querySelector('#results');
const generateButton = document.querySelector('#generate');

function renumberRows() {
  [...tableBody.rows].forEach((row, index) => row.querySelector('.row-number').textContent = index + 1);
}

function addRow(values = {}) {
  const row = template.content.firstElementChild.cloneNode(true);
  for (const key of ['make', 'model', 'start_year', 'end_year', 'years']) {
    row.querySelector(`.${key.replace('_', '-')}`).value = values[key] || '';
  }
  row.querySelector('.remove-row').addEventListener('click', () => {
    if (tableBody.rows.length === 1) {
      row.querySelectorAll('input').forEach(input => input.value = '');
    } else {
      row.remove();
      renumberRows();
    }
  });
  tableBody.appendChild(row);
  renumberRows();
}

function collectFitments() {
  return [...tableBody.rows].map(row => ({
    make: row.querySelector('.make').value.trim(),
    model: row.querySelector('.model').value.trim(),
    start_year: row.querySelector('.start-year').value.trim(),
    end_year: row.querySelector('.end-year').value.trim(),
    years: row.querySelector('.years').value.trim(),
  })).filter(row => Object.values(row).some(Boolean));
}

function setInput(data) {
  document.querySelector('#sku').value = data.sku || '';
  document.querySelector('#keyword').value = data.core_keyword || '';
  tableBody.replaceChildren();
  (data.fitments || []).forEach(addRow);
  if (!tableBody.rows.length) addRow();
  statusNode.textContent = data.sku ? `已载入 ${data.sku}` : '新建 SKU';
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `请求失败 (${response.status})`);
  return body;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function badge(value) {
  const className = String(value).toLowerCase().replaceAll(' ', '-');
  return `<span class="badge ${className}">${escapeHtml(value)}</span>`;
}

function renderTable(rows, columns) {
  if (!rows.length) return '<div class="empty">暂无结果</div>';
  const header = columns.map(column => `<th>${escapeHtml(column.label)}</th>`).join('');
  const body = rows.map(row => `<tr>${columns.map(column => {
    let value = row[column.key];
    if (column.percent && value !== null && value !== '') value = `${(Number(value) * 100).toFixed(1)}%`;
    if (column.number && value !== null && value !== '') value = Number(value).toLocaleString('en-US');
    const content = column.badge ? badge(value) : escapeHtml(value ?? '');
    return `<td class="${column.long ? 'long' : ''}">${content}</td>`;
  }).join('')}</tr>`).join('');
  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderResults(data) {
  const metrics = [
    ['排名实体', data.summary.ranking_entities],
    ['Core Listing', data.summary.core_listings],
    ['Discovery Listing', data.summary.discovery_listings],
    ['Mixed Listing', data.summary.mixed_listings ?? 0],
    ['PLP 关键词', data.summary.plp_keywords],
    ['数据缺口', data.summary.data_gaps],
  ];
  document.querySelector('#metrics').innerHTML = metrics.map(([label, value], index) =>
    `<div class="metric ${index === 5 && value ? 'warning' : ''}"><strong>${value}</strong><span>${label}</span></div>`
  ).join('');

  const preferred = [`${data.sku}-Listing与PLP矩阵.xlsx`, 'listing_matrix.csv', 'vehicle_ranking.csv'];
  const fileRank = (name) => {
    const index = preferred.indexOf(name);
    return index === -1 ? preferred.length : index;
  };
  const files = [...data.files].sort((a, b) => fileRank(a.name) - fileRank(b.name));
  document.querySelector('#downloads').innerHTML = files.slice(0, 5).map(file =>
    `<a class="download-link" href="${escapeHtml(file.url)}">${escapeHtml(file.label || file.name)}</a>`
  ).join('');

  document.querySelector('#listings-panel').innerHTML = renderTable(data.listing_matrix, [
    {key:'Listing ID', label:'Listing ID'}, {key:'Listing Type', label:'类型', badge:true},
    {key:'Vehicle', label:'车型'}, {key:'Title', label:'标题', long:true},
    {key:'Compatibility Scope', label:'Compatibility', long:true},
  ]);
  document.querySelector('#ranking-panel').innerHTML = renderTable(data.vehicle_ranking, [
    {key:'Rank', label:'排名'}, {key:'Make', label:'品牌'}, {key:'Model / Family', label:'车型 / 家族'},
    {key:'Fitment Years', label:'适配年份'}, {key:'US Historical Sales', label:'美国历史销量', number:true},
    {key:'Estimated Effective Population', label:'估算有效保有量', number:true},
    {key:'Population Reference Year', label:'估算基准年'},
    {key:'Market Tier', label:'市场等级', badge:true}, {key:'Relative Market Size', label:'相对市场', percent:true},
    {key:'Coverage', label:'覆盖率', percent:true}, {key:'Data Status', label:'数据状态', badge:true},
    {key:'Core / Discovery', label:'分组', badge:true}, {key:'Decision Reason', label:'决策原因', long:true},
  ]);
  resultsSection.hidden = false;
  statusNode.textContent = `${data.sku} 处理完成`;
  resultsSection.scrollIntoView({behavior: 'smooth', block: 'start'});
}

async function loadSku(sku) {
  validationNode.textContent = '';
  try {
    const data = await fetchJson(`/api/input?sku=${encodeURIComponent(sku)}`);
    setInput(data);
    try { renderResults(await fetchJson(`/api/results?sku=${encodeURIComponent(sku)}`)); } catch (_) {}
  } catch (error) {
    validationNode.textContent = error.message;
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (quoted && char === '"' && text[index + 1] === '"') { field += '"'; index++; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { row.push(field); field = ''; }
    else if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && text[index + 1] === '\n') index++;
      row.push(field); field = '';
      if (row.some(cell => cell.trim())) rows.push(row);
      row = [];
    } else field += char;
  }
  row.push(field); if (row.some(cell => cell.trim())) rows.push(row);
  if (rows.length < 2) throw new Error('CSV 中没有适配数据');
  const headers = rows.shift().map(value => value.trim().toLowerCase());
  const required = ['sku', 'core_keyword', 'make', 'model'];
  if (required.some(key => !headers.includes(key))) throw new Error('CSV 缺少 sku、core_keyword、make 或 model 列');
  const objects = rows.map(values => Object.fromEntries(headers.map((header, index) => [header, (values[index] || '').trim()])));
  return {sku: objects[0].sku, core_keyword: objects[0].core_keyword, fitments: objects};
}

document.querySelector('#add-row').addEventListener('click', () => addRow());
document.querySelector('#import-button').addEventListener('click', () => document.querySelector('#csv-input').click());
document.querySelector('#csv-input').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try { setInput(parseCsv(await file.text())); validationNode.textContent = ''; }
  catch (error) { validationNode.textContent = error.message; }
  event.target.value = '';
});

generateButton.addEventListener('click', async () => {
  validationNode.textContent = '';
  const payload = {
    sku: document.querySelector('#sku').value.trim(),
    core_keyword: document.querySelector('#keyword').value.trim(),
    refresh_sales: document.querySelector('#refresh-sales').checked,
    fitments: collectFitments(),
  };
  generateButton.disabled = true;
  generateButton.textContent = '正在生成...';
  statusNode.textContent = '正在查询销量并生成矩阵';
  statusNode.classList.add('busy');
  try {
    renderResults(await fetchJson('/api/process', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}));
  } catch (error) {
    validationNode.textContent = error.message;
    statusNode.textContent = '处理失败';
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = '生成 Listing 与广告矩阵';
    statusNode.classList.remove('busy');
  }
});

document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === tab));
  document.querySelector('#listings-panel').hidden = tab.dataset.tab !== 'listings';
  document.querySelector('#ranking-panel').hidden = tab.dataset.tab !== 'ranking';
}));

addRow();
