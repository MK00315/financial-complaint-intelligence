export const FIRST = '2025-01-01';
export const LAST = '2025-02-28';
const number = new Intl.NumberFormat('en-US');
export const n = value => number.format(Number(value) || 0);
export const pct = (value, digits = 1) => {
  const amount=Number(value || 0),minimum=10**(-digits);
  return amount>0 && amount<minimum ? `<${minimum.toFixed(digits)}%` : `${amount.toFixed(digits)}%`;
};
export const score = value => Number(value || 0).toFixed(4);
export function e(value = '') {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
export const shortNames = {
  'Credit reporting or other personal consumer reports':'Credit reporting',
  'Money transfer, virtual currency, or money service':'Money transfers',
  'Checking or savings account':'Checking/savings',
  'Payday loan, title loan, personal loan, or advance loan':'Payday/personal loans',
  'Debt or credit management':'Debt/credit management',
};
export const shortProduct = name => shortNames[name] || name;
export function dateLabel(iso, year = false) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', {month:'short',day:'numeric',...(year?{year:'numeric'}:{}),timeZone:'UTC'});
}
export const rangeLabel = (start, end) => start === end ? dateLabel(start, true) : `${dateLabel(start)}–${dateLabel(end, true)}`;
export function weekLabel(start) {
  const end = new Date(`${start}T00:00:00Z`); end.setUTCDate(end.getUTCDate() + 6);
  return rangeLabel(start, end.toISOString().slice(0,10));
}
export function params(values) {
  return new URLSearchParams(Object.entries(values).filter(([,value]) => value !== '' && value != null)).toString();
}
export async function getJSON(url, options = {}) {
  const response = await fetch(url, options);
  let value;
  try { value = await response.json(); } catch { throw new Error('The workspace could not read the server response. Please try again.'); }
  if (!response.ok) {
    const message = Array.isArray(value.detail) ? value.detail.map(item => item.msg).join(' ') : value.detail;
    throw new Error(message || 'The request could not be completed. Please try again.');
  }
  return value;
}
export function issueMatches(rows, query = '', sort = 'count_desc') {
  const search = query.trim().toLocaleLowerCase('en-US');
  const result = rows.filter(row => `${row.issue} ${row.product}`.toLocaleLowerCase('en-US').includes(search));
  return result.sort((a,b) => sort === 'issue_asc' ? a.issue.localeCompare(b.issue) || a.product.localeCompare(b.product)
    : sort === 'count_asc' ? a.complaints-b.complaints || a.issue.localeCompare(b.issue)
    : b.complaints-a.complaints || a.issue.localeCompare(b.issue));
}
