// Progressive enhancements. Navigation, answers, and screenshot links work without JavaScript.
(() => {
  document.documentElement.classList.add('js');

  function initMobileNavigation() {
    const menuButton = document.querySelector('[data-menu-toggle]');
    const navigation = document.querySelector('#site-navigation');
    menuButton?.addEventListener('click', () => {
      const open = menuButton.getAttribute('aria-expanded') !== 'true';
      menuButton.setAttribute('aria-expanded', String(open));
      navigation?.classList.toggle('is-open', open);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
        menuButton.setAttribute('aria-expanded', 'false');
        navigation?.classList.remove('is-open');
        menuButton.focus();
      }
    });
  }

  function initShortcutDemo() {
    // This is an example configuration; the preview never controls a visitor's device.
    const demo = document.querySelector('[data-shortcut-demo]');
    if (!demo) return;
    const examples = {
      keystar: [
        { trigger: 'Single', label: 'Volume Up · Single Press', action: 'Play / Pause', description: 'Control your music with a single press.' },
        { trigger: 'Double', label: 'Volume Down · Double Press', action: 'Sound Mode', description: 'Switch sound modes on the lock screen.' },
        { trigger: 'Long', label: 'Power · Long Press', action: 'Torch', description: 'Toggle the torch instantly.' },
      ],
      penstar: [
        { trigger: 'Single', label: 'S Pen · Single Press', action: 'Play / Pause', description: 'Play or pause the current reel in Instagram.' },
        { trigger: 'Up', label: 'S Pen · Up Gesture', action: 'Next Reel', description: 'Scroll to the next reel in Instagram.' },
        { trigger: 'Down', label: 'S Pen · Down Gesture', action: 'Previous Reel', description: 'Scroll to the previous reel in Instagram.' },
      ],
    };
    const action = demo.querySelector('[data-demo-action]');
    const description = demo.querySelector('[data-demo-description]');
    const label = demo.querySelector('[data-demo-label]');
    const hardware = demo.querySelector('[data-demo-hardware]');
    const triggers = demo.querySelector('.demo-triggers');
    const appButtons = demo.querySelectorAll('[data-demo-app]');
    const triggerButtons = demo.querySelectorAll('[data-demo-trigger]');
    let app = 'keystar';
    let trigger = 0;
    const update = () => {
      const example = examples[app][trigger];
      action.textContent = example.action;
      description.textContent = example.description;
      label.textContent = example.label;
      hardware.classList.toggle('pen', app === 'penstar');
      hardware.classList.toggle('power', app === 'keystar' && trigger === 2);
      triggers.setAttribute('aria-label', app === 'keystar' ? 'Preview a press pattern' : 'Preview an S Pen gesture');
      appButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.demoApp === app)));
      triggerButtons.forEach((button) => {
        const index = Number(button.dataset.demoTrigger);
        button.textContent = examples[app][index].trigger;
        button.setAttribute('aria-pressed', String(index === trigger));
      });
    };
    appButtons.forEach((button) => button.addEventListener('click', () => { app = button.dataset.demoApp; update(); }));
    triggerButtons.forEach((button) => button.addEventListener('click', () => { trigger = Number(button.dataset.demoTrigger); update(); }));
    update();
  }

  function initSupportSearch() {
    const normalise = (text) => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
    document.querySelectorAll('[data-support-search]').forEach((input) => {
      const items = [...document.querySelectorAll('.faq-item')];
      const status = document.querySelector('[data-search-status]');
      const empty = document.querySelector('[data-search-empty]');
      const initialOpen = new Set(items.filter((item) => item.open));
      const filter = () => {
        const query = normalise(input.value.trim());
        let count = 0;
        items.forEach((item) => {
          const match = !query || normalise(item.textContent).includes(query);
          item.hidden = !match;
          if (match) count += 1;
          item.open = query ? match : initialOpen.has(item);
        });
        status.textContent = query ? `${count} ${count === 1 ? 'answer' : 'answers'} found` : `${items.length} answers`;
        empty.hidden = count > 0;
      };
      input.addEventListener('input', filter);
      const revealHash = () => {
        let id;
        try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
        if (!id) return;
        const target = document.getElementById(id);
        const item = target?.closest('.faq-item');
        if (!item) return;
        if (input.value) { input.value = ''; filter(); }
        item.open = true;
        initialOpen.add(item);
        requestAnimationFrame(() => item.scrollIntoView({ block: 'start' }));
      };
      window.addEventListener('hashchange', revealHash);
      revealHash();
    });
  }

  function initScreenshotViewer() {
    const imageDialog = document.querySelector('[data-image-dialog]');
    if (imageDialog && typeof imageDialog.showModal === 'function') {
      let opener;
      document.querySelectorAll('[data-enlarge-image]').forEach((button) => button.addEventListener('click', (event) => {
        event.preventDefault();
        opener = button;
        const original = button.querySelector('img');
        const image = imageDialog.querySelector('img');
        image.src = button.dataset.enlargeImage;
        image.alt = original.alt;
        imageDialog.showModal();
      }));
      imageDialog.querySelector('[data-dialog-close]').addEventListener('click', () => imageDialog.close());
      imageDialog.addEventListener('click', (event) => { if (event.target === imageDialog) imageDialog.close(); });
      imageDialog.addEventListener('close', () => opener?.focus());
    }
  }

  initMobileNavigation();
  initShortcutDemo();
  initSupportSearch();
  initScreenshotViewer();
})();
