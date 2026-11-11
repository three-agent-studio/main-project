/* Progressive enhancement only: native form submission works without JavaScript.
 * Keep this entry independent of React so authentication never waits for the SPA. */
(() => {
  const form = document.querySelector('[data-login-form]');
  const password = document.getElementById('id_password');
  const toggle = document.querySelector('[data-password-toggle]');

  if (password && toggle) {
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const reveal = password.type === 'password';
      password.type = reveal ? 'text' : 'password';
      toggle.setAttribute('aria-pressed', String(reveal));
      toggle.setAttribute('aria-label', reveal ? 'Скрыть пароль' : 'Показать пароль');
    });
  }

  if (!form) return;
  const submit = form.querySelector('[data-submit-button]');
  const label = form.querySelector('[data-submit-label]');
  const status = form.querySelector('[data-submit-status]');
  const reset = () => {
    submit.disabled = false;
    form.removeAttribute('aria-busy');
    label.textContent = 'Войти';
    status.textContent = '';
    // Never restore a revealed password when returning via browser history.
    if (password && toggle) {
      password.type = 'password';
      toggle.setAttribute('aria-pressed', 'false');
      toggle.setAttribute('aria-label', 'Показать пароль');
    }
  };
  form.addEventListener('submit', () => {
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    label.textContent = 'Входим…';
    status.textContent = 'Выполняется вход в кабинет';
  });
  window.addEventListener('pageshow', reset);
  document.querySelector('[data-login-error]')?.focus();
})();
