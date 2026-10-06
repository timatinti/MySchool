const root = document.documentElement;
const form = document.querySelector('#authForm');
const loginTab = document.querySelector('#loginTab');
const registerTab = document.querySelector('#registerTab');
const switchButton = document.querySelector('#switchButton');
const nameField = document.querySelector('#nameField');
const loginExtra = document.querySelector('#loginExtra');
const status = document.querySelector('#status');
let mode = 'login';

const copy = {
  login: { eyebrow: 'С возвращением', title: 'Войти в дневник', subtitle: 'Продолжи свой учебный день.', button: 'Войти', switch: 'Нет аккаунта?', action: 'Заведите его!' },
  register: { eyebrow: 'Первый шаг', title: 'Создать аккаунт', subtitle: 'Собери свой учебный день в одном месте.', button: 'Зарегистрироваться', switch: 'Уже есть аккаунт?', action: 'Войдите в него!' },
};

function setMode(nextMode) {
  mode = nextMode;
  const c = copy[mode];
  document.querySelector('#formEyebrow').textContent = c.eyebrow;
  document.querySelector('#formTitle').textContent = c.title;
  document.querySelector('#formSubtitle').textContent = c.subtitle;
  document.querySelector('#submitButton').firstChild.textContent = `${c.button} `;
  document.querySelector('#switchCopy').firstChild.textContent = `${c.switch} `;
  switchButton.textContent = c.action;
  nameField.classList.toggle('hidden', mode === 'login');
  loginExtra.classList.toggle('hidden', mode === 'register');
  loginTab.classList.toggle('active', mode === 'login');
  registerTab.classList.toggle('active', mode === 'register');
  document.querySelector('#password').autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  status.textContent = '';
}

loginTab.addEventListener('click', () => setMode('login'));
registerTab.addEventListener('click', () => setMode('register'));
switchButton.addEventListener('click', () => setMode(mode === 'login' ? 'register' : 'login'));

document.querySelector('#showPassword').addEventListener('click', (event) => {
  const password = document.querySelector('#password');
  const visible = password.type === 'text';
  password.type = visible ? 'password' : 'text';
  event.currentTarget.textContent = visible ? '◉' : '◌';
});

document.querySelector('#themeToggle').addEventListener('click', () => {
  const dark = root.classList.toggle('dark');
  localStorage.setItem('diary-theme', dark ? 'dark' : 'light');
  document.querySelector('#themeIcon').textContent = dark ? '☀' : '☾';
  document.querySelector('#themeLabel').textContent = dark ? 'Дневная тема' : 'Ночная тема';
});

if (localStorage.getItem('diary-theme') === 'dark') document.querySelector('#themeToggle').click();

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  status.className = 'status';
  const email = document.querySelector('#email').value.trim();
  const password = document.querySelector('#password').value;
  const name = document.querySelector('#name').value.trim();
  if (!email || !password || (mode === 'register' && !name)) {
    status.textContent = 'Заполни, пожалуйста, все поля.';
    return;
  }
  const button = document.querySelector('#submitButton');
  button.disabled = true;
  try {
    const response = await fetch(`/api/${mode}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({email, password, name}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Что-то пошло не так');
    status.className = 'status success';
    status.textContent = `${data.message}. Скоро здесь появится твой дневник.`;
    if (mode === 'register') setTimeout(() => setMode('login'), 1200);
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});
