const form = document.getElementById('loginForm');
const message = document.getElementById('loginMessage');

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  const original = button.innerHTML;
  button.disabled = true;
  button.textContent = '正在建立安全连接…';
  message.textContent = '';
  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
      }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || '登录失败');
    location.replace('/');
  } catch (error) {
    message.textContent = error.message;
    button.disabled = false;
    button.innerHTML = original;
  }
});
