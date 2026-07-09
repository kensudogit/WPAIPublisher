(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var hero = document.getElementById('hero');
    if (!hero) return;

    hero.style.opacity = '0';
    hero.style.transition = 'opacity 0.6s ease';

    requestAnimationFrame(function () {
      hero.style.opacity = '1';
    });
  });
})();
