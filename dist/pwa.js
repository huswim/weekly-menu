(() => {
  const installButton = document.getElementById('installApp');
  const installHelp = document.getElementById('installHelp');
  const offlineStatus = document.getElementById('offlineStatus');
  const updateNotice = document.getElementById('appUpdate');
  const updateButton = document.getElementById('applyUpdate');
  const standalone = window.matchMedia('(display-mode: standalone)');
  let installPrompt = null;
  let waitingWorker = null;
  let reloadAfterUpdate = false;

  function refreshInstallButton() {
    const installed = standalone.matches || navigator.standalone === true;
    installButton.classList.toggle('hidden', installed || !installPrompt);
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    installHelp.classList.toggle('hidden', installed || ios);
  }
  refreshInstallButton();
  standalone.addEventListener('change', refreshInstallButton);
  function refreshOfflineStatus() {
    offlineStatus.classList.toggle('hidden', navigator.onLine);
  }
  refreshOfflineStatus();
  window.addEventListener('online', refreshOfflineStatus);
  window.addEventListener('offline', refreshOfflineStatus);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    refreshInstallButton();
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    installButton.classList.add('hidden');
    installHelp.classList.add('hidden');
  });
  installButton.addEventListener('click', async () => {
    if (!installPrompt) {
      installHelp.open = true;
      installHelp.scrollIntoView({ block: 'center', behavior: 'instant' });
      return;
    }
    const prompt = installPrompt;
    installPrompt = null;
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      if (choice.outcome === 'accepted') installButton.classList.add('hidden');
    } catch {
      installHelp.open = true;
      installHelp.scrollIntoView({ block: 'center', behavior: 'instant' });
    }
  });

  if (!('serviceWorker' in navigator)) return;
  function offerUpdate(worker) {
    waitingWorker = worker;
    updateNotice.classList.remove('hidden');
  }
  updateButton.addEventListener('click', () => {
    if (!waitingWorker) return;
    reloadAfterUpdate = true;
    updateButton.disabled = true;
    updateButton.textContent = '업데이트 중…';
    waitingWorker.postMessage({ type: 'SKIP_WAITING' });
  });
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadAfterUpdate) window.location.reload();
  });
  navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' })
    .then(registration => {
      if (registration.waiting && navigator.serviceWorker.controller) offerUpdate(registration.waiting);
      registration.addEventListener('updatefound', () => {
        const worker = registration.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) offerUpdate(worker);
        });
      });
    })
    .catch(() => {
      const note = document.createElement('p');
      note.textContent = '오프라인 저장을 시작하지 못했습니다. 온라인 상태에서 다시 열어 주세요.';
      installHelp.append(note);
    });
})();
