async function renderCart(items) {
  const res = await fetch('/api/checkout', {method: 'POST', body: JSON.stringify(items)});
  const data = await res.json();
  document.getElementById('total').textContent = data.total;
}
