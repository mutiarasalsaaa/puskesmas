// Sidebar toggle
const sidebar = document.getElementById('sidebar');
const pageContent = document.getElementById('page-content');
const toggleBtn = document.getElementById('sidebarToggle');

if (toggleBtn) {
  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      sidebar && sidebar.classList.toggle('open');
    } else {
      sidebar && sidebar.classList.toggle('collapsed');
      pageContent && pageContent.classList.toggle('full');
    }
  });
}

// Close sidebar on mobile overlay click
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
    if (!sidebar.contains(e.target) && e.target !== toggleBtn) {
      sidebar.classList.remove('open');
    }
  }
});

// Current date display
const dateEl = document.getElementById('current-date');
if (dateEl) {
  const now = new Date();
  const opts = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  dateEl.textContent = now.toLocaleDateString('id-ID', opts);
}

// Auto-dismiss alerts after 4 seconds
document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
    if (bsAlert) bsAlert.close();
  }, 4000);
});
// SALAH (tanpa slash di depan):
fetch(`api/arsip-rm/${NO_RM}`)

// BENAR (dengan slash di depan):
fetch(`/api/arsip-rm/${NO_RM}`)