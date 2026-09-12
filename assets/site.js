// Navigation enhances ordinary anchor links; all content is available without JS.
const header = document.querySelector('.header');
const sections = [...document.querySelectorAll('main > .page')];
const links = [...document.querySelectorAll('.nav-link')];
const progress = document.getElementById('scrollProgress');
let scheduled = false;

function updateNavigation() {
    const offset = header.getBoundingClientRect().height + 24;
    let current = sections[0];
    for (const section of sections) {
        if (section.getBoundingClientRect().top <= offset) current = section;
    }
    for (const link of links) {
        const active = link.hash === `#${current.id}`;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
    }
    const distance = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.transform = `scaleX(${distance > 0 ? window.scrollY / distance : 0})`;
    scheduled = false;
}

function scheduleUpdate() {
    if (!scheduled) {
        scheduled = true;
        requestAnimationFrame(updateNavigation);
    }
}

for (const link of document.querySelectorAll('.language-switch a')) {
    link.addEventListener('click', () => {
        if (document.getElementById(location.hash.slice(1))) {
            link.hash = location.hash;
        }
    });
}

window.addEventListener('scroll', scheduleUpdate, { passive: true });
window.addEventListener('resize', scheduleUpdate);
window.addEventListener('load', scheduleUpdate);
updateNavigation();
