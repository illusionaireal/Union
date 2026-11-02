// Read-only document interactions; no API calls or persistent browser storage.
const announce = (text) => {
  const message = document.getElementById('copy-message');
  message.textContent = text;
  window.clearTimeout(announce.timer);
  announce.timer = window.setTimeout(() => { message.textContent = ''; }, 2600);
};
for (const button of document.querySelectorAll('.copy-command')) {
  button.addEventListener('click', async () => {
    const code = button.closest('.code-block').querySelector('code');
    try {
      await navigator.clipboard.writeText(code.textContent);
      announce('命令已复制');
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection.removeAllRanges();
      selection.addRange(range);
      announce('无法自动复制，已选中命令，请手动复制');
    }
  });
}
document.getElementById('print-document').addEventListener('click', () => window.print());
const chapterLinks = [...document.querySelectorAll('[data-chapter]')];
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (!visible.length) return;
    for (const link of chapterLinks) {
      if (link.dataset.chapter === visible[0].target.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }, { rootMargin: '-90px 0px -65% 0px', threshold: 0 });
  for (const section of document.querySelectorAll('.doc-section')) observer.observe(section);
}
