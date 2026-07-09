document.addEventListener('DOMContentLoaded', () => {
  const hero = document.getElementById('hero');
  if (!hero) return;

  hero.style.opacity = '0';
  hero.style.transition = 'opacity 0.6s ease';

  requestAnimationFrame(() => {
    hero.style.opacity = '1';
  });
});
