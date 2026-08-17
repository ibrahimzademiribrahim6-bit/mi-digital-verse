# ============================================================
#  Mi Digital Verse — Complete UI/UX Overhaul
#  Part 1: BASE_HTML + INDEX_HTML
#  All Azerbaijani strings preserved exactly as in original.
# ============================================================

BASE_HTML = """
<!DOCTYPE html>
<html lang="az" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Mi Digital Verse{% endblock %}</title>

    <!-- Google Fonts: Orbitron (display) + Inter (body) + JetBrains Mono (numbers/data) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
    /* ═══════════════════════════════════════════════════════
       DESIGN TOKEN SYSTEM
       ═══════════════════════════════════════════════════════ */
    :root {
        /* --- DARK THEME TOKENS (default) --- */
        --void:          #080B14;
        --void-2:        #0E1425;
        --void-3:        #141D35;
        --surface:       #111827;
        --surface-2:     #1A2540;
        --surface-3:     #1E2D4A;
        --border:        rgba(0, 212, 255, 0.12);
        --border-hover:  rgba(0, 212, 255, 0.35);

        --pulse:         #00D4FF;
        --pulse-dim:     rgba(0, 212, 255, 0.15);
        --pulse-glow:    0 0 20px rgba(0, 212, 255, 0.4);
        --pulse-dark:    #0099C8;

        --ember:         #FF4D6D;
        --ember-dim:     rgba(255, 77, 109, 0.15);
        --ember-glow:    0 0 20px rgba(255, 77, 109, 0.4);

        --gold:          #FFD166;
        --gold-dim:      rgba(255, 209, 102, 0.15);
        --violet:        #A855F7;
        --violet-dim:    rgba(168, 85, 247, 0.15);
        --green:         #22D3A5;
        --green-dim:     rgba(34, 211, 165, 0.15);

        --ink:           #F0F4FF;
        --ink-2:         #A8B8D8;
        --ink-3:         #6B7FA3;
        --ink-muted:     #3D4F6E;

        --radius-sm:     6px;
        --radius-md:     12px;
        --radius-lg:     20px;
        --radius-xl:     28px;

        --font-display:  'Orbitron', sans-serif;
        --font-body:     'Inter', sans-serif;
        --font-mono:     'JetBrains Mono', monospace;

        --nav-height:    64px;
        --transition:    all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        --glass:         rgba(14, 20, 37, 0.75);
        --glass-border:  rgba(0, 212, 255, 0.1);
    }

    /* --- LIGHT THEME TOKENS --- */
    [data-theme="light"] {
        --void:          #EEF4FF;
        --void-2:        #E4ECFC;
        --void-3:        #D8E6FF;
        --surface:       #FFFFFF;
        --surface-2:     #F0F6FF;
        --surface-3:     #E8F0FE;
        --border:        rgba(0, 110, 180, 0.14);
        --border-hover:  rgba(0, 110, 180, 0.4);

        --pulse:         #0077AA;
        --pulse-dim:     rgba(0, 119, 170, 0.12);
        --pulse-glow:    0 0 20px rgba(0, 119, 170, 0.25);
        --pulse-dark:    #005580;

        --ember:         #E8274A;
        --ember-dim:     rgba(232, 39, 74, 0.1);
        --ember-glow:    0 0 20px rgba(232, 39, 74, 0.25);

        --gold:          #B45309;
        --gold-dim:      rgba(180, 83, 9, 0.1);
        --violet:        #7C3AED;
        --violet-dim:    rgba(124, 58, 237, 0.1);
        --green:         #059669;
        --green-dim:     rgba(5, 150, 105, 0.1);

        --ink:           #0D1B2A;
        --ink-2:         #2C3E58;
        --ink-3:         #4A607A;
        --ink-muted:     #8BA0B8;

        --glass:         rgba(255, 255, 255, 0.82);
        --glass-border:  rgba(0, 110, 180, 0.12);
    }

    /* ═══════════════════════════════════════════════════════
       GLOBAL RESET & BASE
       ═══════════════════════════════════════════════════════ */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html { scroll-behavior: smooth; }

    body {
        font-family: var(--font-body);
        background: var(--void);
        color: var(--ink);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
        transition: background 0.3s ease, color 0.3s ease;
    }

    /* Animated gradient mesh background */
    body::before {
        content: '';
        position: fixed;
        inset: 0;
        z-index: -1;
        background:
            radial-gradient(ellipse 60% 40% at 20% 10%, rgba(0, 212, 255, 0.06) 0%, transparent 70%),
            radial-gradient(ellipse 40% 50% at 80% 80%, rgba(168, 85, 247, 0.05) 0%, transparent 70%),
            radial-gradient(ellipse 50% 30% at 60% 20%, rgba(255, 77, 109, 0.04) 0%, transparent 70%);
        pointer-events: none;
    }

    [data-theme="light"] body::before {
        background:
            radial-gradient(ellipse 60% 40% at 20% 10%, rgba(0, 119, 170, 0.07) 0%, transparent 70%),
            radial-gradient(ellipse 40% 50% at 80% 80%, rgba(124, 58, 237, 0.05) 0%, transparent 70%),
            radial-gradient(ellipse 50% 30% at 60% 20%, rgba(232, 39, 74, 0.04) 0%, transparent 70%);
    }

    a { color: inherit; text-decoration: none; }
    img { max-width: 100%; display: block; }
    button { cursor: pointer; border: none; background: none; font-family: inherit; }

    /* ═══════════════════════════════════════════════════════
       TYPOGRAPHY
       ═══════════════════════════════════════════════════════ */
    .font-display { font-family: var(--font-display); }
    .font-mono    { font-family: var(--font-mono); }

    h1, h2, h3 { line-height: 1.2; font-weight: 700; }

    /* Signature element: CRT chromatic-aberration glow on brand name */
    .brand-logo {
        font-family: var(--font-display);
        font-weight: 900;
        font-size: 1.35rem;
        color: var(--pulse);
        letter-spacing: 0.03em;
        text-shadow:
            -1px 0 rgba(255, 77, 109, 0.6),
             1px 0 rgba(0, 212, 255, 0.6),
             0 0 18px rgba(0, 212, 255, 0.5);
        transition: var(--transition);
    }
    .brand-logo:hover {
        text-shadow:
            -2px 0 rgba(255, 77, 109, 0.8),
             2px 0 rgba(0, 212, 255, 0.8),
             0 0 30px rgba(0, 212, 255, 0.7);
    }

    [data-theme="light"] .brand-logo {
        text-shadow:
            -1px 0 rgba(232, 39, 74, 0.4),
             1px 0 rgba(0, 119, 170, 0.4),
             0 0 12px rgba(0, 119, 170, 0.3);
    }

    /* ═══════════════════════════════════════════════════════
       NAVIGATION
       ═══════════════════════════════════════════════════════ */
    .nav {
        position: sticky;
        top: 0;
        z-index: 100;
        height: var(--nav-height);
        background: var(--glass);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-bottom: 1px solid var(--glass-border);
        transition: var(--transition);
    }

    .nav-inner {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }

    .nav-links {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .nav-link {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--ink-2);
        padding: 0.4rem 0.75rem;
        border-radius: var(--radius-sm);
        transition: var(--transition);
        position: relative;
    }
    .nav-link:hover {
        color: var(--pulse);
        background: var(--pulse-dim);
    }
    .nav-link.active { color: var(--pulse); }

    /* Dropdown */
    .nav-dropdown { position: relative; }
    .nav-dropdown-btn {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--ink-2);
        padding: 0.4rem 0.75rem;
        border-radius: var(--radius-sm);
        transition: var(--transition);
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    .nav-dropdown-btn:hover { color: var(--pulse); background: var(--pulse-dim); }
    .nav-dropdown-btn .chevron {
        font-size: 0.65rem;
        transition: transform 0.2s;
    }
    .nav-dropdown:hover .chevron { transform: rotate(180deg); }

    .nav-dropdown-menu {
        position: absolute;
        top: calc(100% + 8px);
        left: 0;
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.5rem;
        min-width: 160px;
        opacity: 0;
        visibility: hidden;
        transform: translateY(-6px);
        transition: var(--transition);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .nav-dropdown:hover .nav-dropdown-menu {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
    }
    .nav-dropdown-menu a {
        display: block;
        padding: 0.45rem 0.75rem;
        font-size: 0.85rem;
        color: var(--ink-2);
        border-radius: var(--radius-sm);
        transition: var(--transition);
    }
    .nav-dropdown-menu a:hover {
        color: var(--pulse);
        background: var(--pulse-dim);
    }

    /* Nav actions */
    .nav-actions {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .nav-icon-btn {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-sm);
        background: var(--surface-2);
        border: 1px solid var(--border);
        color: var(--ink-2);
        font-size: 0.9rem;
        transition: var(--transition);
        position: relative;
        text-decoration: none;
    }
    .nav-icon-btn:hover {
        border-color: var(--border-hover);
        color: var(--pulse);
        box-shadow: var(--pulse-glow);
    }

    .nav-notif-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        background: var(--ember);
        color: #fff;
        font-size: 0.6rem;
        font-family: var(--font-mono);
        font-weight: 700;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid var(--void);
    }

    .nav-btn-admin {
        font-size: 0.78rem;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: var(--radius-sm);
        background: var(--gold-dim);
        border: 1px solid rgba(255, 209, 102, 0.3);
        color: var(--gold);
        transition: var(--transition);
        font-family: var(--font-mono);
        letter-spacing: 0.05em;
    }
    .nav-btn-admin:hover {
        background: var(--gold);
        color: #000;
        box-shadow: 0 0 16px rgba(255, 209, 102, 0.5);
    }

    .nav-btn-logout {
        font-size: 0.78rem;
        font-weight: 500;
        padding: 0.35rem 0.75rem;
        border-radius: var(--radius-sm);
        background: var(--ember-dim);
        border: 1px solid rgba(255, 77, 109, 0.2);
        color: var(--ember);
        transition: var(--transition);
    }
    .nav-btn-logout:hover {
        background: var(--ember);
        color: #fff;
        box-shadow: var(--ember-glow);
    }

    .nav-btn-login {
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.45rem 1.1rem;
        border-radius: var(--radius-sm);
        background: linear-gradient(135deg, var(--pulse), var(--pulse-dark));
        color: var(--void);
        border: none;
        transition: var(--transition);
        letter-spacing: 0.02em;
    }
    .nav-btn-login:hover {
        opacity: 0.9;
        box-shadow: var(--pulse-glow);
        transform: translateY(-1px);
    }

    /* ═══════════════════════════════════════════════════════
       MOBILE NAV
       ═══════════════════════════════════════════════════════ */
    .mobile-menu-btn {
        display: none;
        width: 36px;
        height: 36px;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-sm);
        background: var(--surface-2);
        border: 1px solid var(--border);
        color: var(--ink-2);
        font-size: 1.1rem;
        transition: var(--transition);
    }
    .mobile-menu-btn:hover { border-color: var(--border-hover); color: var(--pulse); }

    .mobile-menu {
        display: none;
        background: var(--glass);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid var(--glass-border);
        padding: 1rem 1.5rem 1.5rem;
    }
    .mobile-menu.open { display: block; }
    .mobile-menu a,
    .mobile-menu button {
        display: block;
        padding: 0.65rem 0.5rem;
        color: var(--ink-2);
        font-size: 0.9rem;
        border-bottom: 1px solid var(--border);
        transition: var(--transition);
        width: 100%;
        text-align: left;
        font-family: var(--font-body);
    }
    .mobile-menu a:last-child { border-bottom: none; }
    .mobile-menu a:hover { color: var(--pulse); padding-left: 1rem; }
    .mobile-menu-top {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    @media (max-width: 900px) {
        .nav-links { display: none; }
        .nav-desktop-actions { display: none; }
        .mobile-menu-btn { display: flex; }
    }

    /* ═══════════════════════════════════════════════════════
       LAYOUT CONTAINERS
       ═══════════════════════════════════════════════════════ */
    .container {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
    }
    .page-content { padding: 2.5rem 0 4rem; }

    main { flex: 1; }

    /* ═══════════════════════════════════════════════════════
       CARD SYSTEM (Glassmorphism)
       ═══════════════════════════════════════════════════════ */
    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        overflow: hidden;
        transition: var(--transition);
    }
    .card:hover {
        border-color: var(--border-hover);
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35), var(--pulse-glow);
    }

    .card-glass {
        background: var(--glass);
        backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-lg);
    }

    .card-inner { padding: 1.5rem; }
    .card-inner-sm { padding: 1rem 1.25rem; }
    .card-inner-lg { padding: 2rem; }

    /* ═══════════════════════════════════════════════════════
       BUTTONS
       ═══════════════════════════════════════════════════════ */
    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.55rem 1.25rem;
        border-radius: var(--radius-sm);
        font-weight: 600;
        font-size: 0.875rem;
        border: 1px solid transparent;
        transition: var(--transition);
        cursor: pointer;
        font-family: var(--font-body);
        letter-spacing: 0.01em;
    }
    .btn-primary {
        background: linear-gradient(135deg, var(--pulse), var(--pulse-dark));
        color: #000;
        border-color: transparent;
    }
    .btn-primary:hover {
        opacity: 0.9;
        box-shadow: var(--pulse-glow);
        transform: translateY(-1px);
    }
    .btn-secondary {
        background: var(--surface-2);
        color: var(--ink-2);
        border-color: var(--border);
    }
    .btn-secondary:hover {
        border-color: var(--border-hover);
        color: var(--pulse);
    }
    .btn-ghost {
        background: transparent;
        color: var(--pulse);
        border-color: var(--border);
    }
    .btn-ghost:hover {
        background: var(--pulse-dim);
        border-color: var(--border-hover);
    }
    .btn-ember {
        background: var(--ember-dim);
        color: var(--ember);
        border-color: rgba(255, 77, 109, 0.25);
    }
    .btn-ember:hover {
        background: var(--ember);
        color: #fff;
        box-shadow: var(--ember-glow);
    }
    .btn-violet {
        background: var(--violet-dim);
        color: var(--violet);
        border-color: rgba(168, 85, 247, 0.25);
    }
    .btn-violet:hover {
        background: var(--violet);
        color: #fff;
        box-shadow: 0 0 16px rgba(168, 85, 247, 0.5);
    }
    .btn-gold {
        background: var(--gold-dim);
        color: var(--gold);
        border-color: rgba(255, 209, 102, 0.25);
    }
    .btn-gold:hover {
        background: var(--gold);
        color: #000;
        box-shadow: 0 0 16px rgba(255, 209, 102, 0.4);
    }
    .btn-green {
        background: var(--green-dim);
        color: var(--green);
        border-color: rgba(34, 211, 165, 0.25);
    }
    .btn-green:hover {
        background: var(--green);
        color: #000;
        box-shadow: 0 0 16px rgba(34, 211, 165, 0.4);
    }
    .btn-danger {
        background: var(--ember-dim);
        color: var(--ember);
        border-color: rgba(255, 77, 109, 0.2);
        padding: 0.3rem 0.7rem;
        font-size: 0.78rem;
    }
    .btn-danger:hover {
        background: var(--ember);
        color: #fff;
    }
    .btn-sm {
        padding: 0.3rem 0.75rem;
        font-size: 0.78rem;
    }
    .btn-lg {
        padding: 0.75rem 1.75rem;
        font-size: 1rem;
        border-radius: var(--radius-md);
    }

    /* ═══════════════════════════════════════════════════════
       FORM ELEMENTS
       ═══════════════════════════════════════════════════════ */
    .form-group { display: flex; flex-direction: column; gap: 0.4rem; }
    .form-label { font-size: 0.8rem; font-weight: 600; color: var(--ink-3); letter-spacing: 0.05em; text-transform: uppercase; }

    .form-input,
    .form-textarea,
    .form-select {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        color: var(--ink);
        font-family: var(--font-body);
        font-size: 0.9rem;
        padding: 0.6rem 0.9rem;
        transition: var(--transition);
        width: 100%;
        outline: none;
    }
    .form-input:focus,
    .form-textarea:focus,
    .form-select:focus {
        border-color: var(--pulse);
        box-shadow: 0 0 0 3px var(--pulse-dim);
    }
    .form-input::placeholder,
    .form-textarea::placeholder { color: var(--ink-muted); }

    .form-textarea { resize: vertical; min-height: 120px; }
    .form-select option { background: var(--surface-2); }

    /* ═══════════════════════════════════════════════════════
       FLASH MESSAGES
       ═══════════════════════════════════════════════════════ */
    .flash-wrap {
        position: fixed;
        top: calc(var(--nav-height) + 12px);
        right: 1.5rem;
        z-index: 200;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        max-width: 360px;
    }
    .flash {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1.1rem;
        background: var(--surface-2);
        border: 1px solid var(--pulse);
        border-radius: var(--radius-md);
        color: var(--ink);
        font-size: 0.875rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), var(--pulse-glow);
        animation: slideInRight 0.3s ease forwards;
    }
    .flash::before { content: '◈'; color: var(--pulse); font-size: 1rem; }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    /* ═══════════════════════════════════════════════════════
       AUTH MODAL
       ═══════════════════════════════════════════════════════ */
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(8, 11, 20, 0.85);
        backdrop-filter: blur(8px);
        z-index: 500;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }
    .modal-overlay.open { display: flex; }

    .modal {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        padding: 2rem;
        width: 100%;
        max-width: 420px;
        position: relative;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
        animation: modalIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    }
    @keyframes modalIn {
        from { opacity: 0; transform: scale(0.94) translateY(12px); }
        to   { opacity: 1; transform: scale(1) translateY(0); }
    }

    .modal-close {
        position: absolute;
        top: 1rem;
        right: 1rem;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: var(--surface-2);
        color: var(--ink-3);
        font-size: 1.1rem;
        transition: var(--transition);
        cursor: pointer;
        border: 1px solid var(--border);
    }
    .modal-close:hover { background: var(--ember); color: #fff; border-color: var(--ember); }

    .modal-tabs {
        display: flex;
        gap: 0.25rem;
        margin-bottom: 1.5rem;
        background: var(--surface-2);
        padding: 0.25rem;
        border-radius: var(--radius-sm);
    }
    .modal-tab {
        flex: 1;
        padding: 0.5rem;
        border-radius: calc(var(--radius-sm) - 2px);
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--ink-3);
        transition: var(--transition);
        text-align: center;
        cursor: pointer;
    }
    .modal-tab.active {
        background: var(--surface);
        color: var(--pulse);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    .modal-form { display: flex; flex-direction: column; gap: 0.85rem; }
    .modal-form.hidden { display: none; }

    /* ═══════════════════════════════════════════════════════
       REPORT MODAL
       ═══════════════════════════════════════════════════════ */
    .report-modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(8, 11, 20, 0.85);
        backdrop-filter: blur(8px);
        z-index: 500;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }
    .report-modal-overlay.open { display: flex; }

    /* ═══════════════════════════════════════════════════════
       BADGE / CHIP SYSTEM
       ═══════════════════════════════════════════════════════ */
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.6rem;
        border-radius: 100px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .chip-pulse  { background: var(--pulse-dim);  color: var(--pulse);  border: 1px solid rgba(0,212,255,0.25); }
    .chip-ember  { background: var(--ember-dim);  color: var(--ember);  border: 1px solid rgba(255,77,109,0.25); }
    .chip-violet { background: var(--violet-dim); color: var(--violet); border: 1px solid rgba(168,85,247,0.25); }
    .chip-gold   { background: var(--gold-dim);   color: var(--gold);   border: 1px solid rgba(255,209,102,0.25); }
    .chip-green  { background: var(--green-dim);  color: var(--green);  border: 1px solid rgba(34,211,165,0.25); }

    /* ═══════════════════════════════════════════════════════
       XP PROGRESS BAR
       ═══════════════════════════════════════════════════════ */
    .xp-bar-track {
        width: 100%;
        height: 6px;
        background: var(--surface-3);
        border-radius: 100px;
        overflow: hidden;
    }
    .xp-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--pulse), var(--violet));
        border-radius: 100px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }
    .xp-bar-fill::after {
        content: '';
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 20px;
        background: rgba(255, 255, 255, 0.3);
        filter: blur(4px);
        border-radius: 100px;
    }

    /* ═══════════════════════════════════════════════════════
       SECTION HEADINGS
       ═══════════════════════════════════════════════════════ */
    .section-heading {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .section-heading h2 {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--ink);
    }
    .section-heading-line {
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, var(--border), transparent);
    }
    .section-heading-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--pulse);
        box-shadow: 0 0 8px var(--pulse);
        flex-shrink: 0;
    }

    /* ═══════════════════════════════════════════════════════
       NEWS CARD (specific)
       ═══════════════════════════════════════════════════════ */
    .news-card {
        display: block;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        overflow: hidden;
        transition: var(--transition);
        position: relative;
    }
    .news-card::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: var(--radius-lg);
        background: linear-gradient(135deg, var(--pulse-dim), transparent 50%);
        opacity: 0;
        transition: opacity 0.3s;
        pointer-events: none;
    }
    .news-card:hover {
        border-color: var(--border-hover);
        transform: translateY(-4px);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4), var(--pulse-glow);
    }
    .news-card:hover::before { opacity: 1; }

    .news-card-body { padding: 1.25rem; }
    .news-card-category {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--pulse);
        margin-bottom: 0.4rem;
        font-family: var(--font-mono);
    }
    .news-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--ink);
        line-height: 1.3;
        margin-bottom: 0.5rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .news-card-meta {
        font-size: 0.75rem;
        color: var(--ink-3);
        font-family: var(--font-mono);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .news-card-meta span { display: flex; align-items: center; gap: 0.25rem; }

    /* ═══════════════════════════════════════════════════════
       MANGA / ANIME CARD
       ═══════════════════════════════════════════════════════ */
    .manga-card {
        display: block;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        overflow: hidden;
        transition: var(--transition);
        position: relative;
    }
    .manga-card:hover {
        border-color: var(--border-hover);
        transform: translateY(-6px);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), var(--pulse-glow);
    }
    .manga-card-img {
        aspect-ratio: 2/3;
        object-fit: cover;
        width: 100%;
    }
    .manga-card-body {
        padding: 0.75rem;
    }
    .manga-card-title {
        font-size: 0.875rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 0.25rem;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .manga-card-sub {
        font-size: 0.72rem;
        color: var(--ink-3);
        font-family: var(--font-mono);
    }
    .manga-card-rating {
        font-family: var(--font-mono);
        font-size: 0.78rem;
        color: var(--gold);
        display: flex;
        align-items: center;
        gap: 0.2rem;
    }

    /* Overlay badge on manga cover */
    .manga-card-badge {
        position: absolute;
        top: 0.5rem;
        left: 0.5rem;
    }

    /* ═══════════════════════════════════════════════════════
       SPOILER
       ═══════════════════════════════════════════════════════ */
    .spoiler {
        background: var(--ink-muted);
        color: var(--ink-muted);
        border-radius: 4px;
        padding: 1px 6px;
        cursor: pointer;
        user-select: none;
        transition: var(--transition);
        filter: blur(3px);
    }
    .spoiler.revealed {
        background: transparent;
        color: var(--ink);
        filter: blur(0);
    }

    /* ═══════════════════════════════════════════════════════
       FOOTER
       ═══════════════════════════════════════════════════════ */
    footer {
        background: var(--surface);
        border-top: 1px solid var(--border);
        padding: 2rem 0;
        margin-top: auto;
    }
    .footer-inner {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
    }
    .footer-brand { font-size: 0.85rem; font-family: var(--font-mono); color: var(--ink-3); }
    .footer-copy  { font-size: 0.78rem; color: var(--ink-muted); }

    /* ═══════════════════════════════════════════════════════
       GRID UTILITIES
       ═══════════════════════════════════════════════════════ */
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.25rem; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.25rem; }
    .col-span-2 { grid-column: span 2; }
    @media (max-width: 900px) {
        .grid-4 { grid-template-columns: repeat(2, 1fr); }
        .grid-3 { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 600px) {
        .grid-4, .grid-3, .grid-2 { grid-template-columns: 1fr; }
        .col-span-2 { grid-column: 1; }
    }

    /* Main layout: sidebar + main */
    .layout-main-sidebar {
        display: grid;
        grid-template-columns: 1fr 320px;
        gap: 2rem;
        align-items: start;
    }
    @media (max-width: 1024px) {
        .layout-main-sidebar { grid-template-columns: 1fr; }
    }

    /* ═══════════════════════════════════════════════════════
       UTILITY
       ═══════════════════════════════════════════════════════ */
    .flex      { display: flex; }
    .items-center { align-items: center; }
    .justify-between { justify-content: space-between; }
    .gap-2     { gap: 0.5rem; }
    .gap-3     { gap: 0.75rem; }
    .gap-4     { gap: 1rem; }
    .mb-1 { margin-bottom: 0.25rem; }
    .mb-2 { margin-bottom: 0.5rem; }
    .mb-3 { margin-bottom: 0.75rem; }
    .mb-4 { margin-bottom: 1rem; }
    .mb-6 { margin-bottom: 1.5rem; }
    .mt-2 { margin-top: 0.5rem; }
    .mt-3 { margin-top: 0.75rem; }
    .mt-4 { margin-top: 1rem; }
    .mt-6 { margin-top: 1.5rem; }
    .mt-8 { margin-top: 2rem; }
    .text-pulse  { color: var(--pulse); }
    .text-ember  { color: var(--ember); }
    .text-gold   { color: var(--gold); }
    .text-violet { color: var(--violet); }
    .text-green  { color: var(--green); }
    .text-muted  { color: var(--ink-3); }
    .text-sm { font-size: 0.875rem; }
    .text-xs { font-size: 0.75rem; }
    .font-bold { font-weight: 700; }
    .hidden { display: none !important; }
    .w-full { width: 100%; }
    .space-y > * + * { margin-top: 0.75rem; }
    .space-y-lg > * + * { margin-top: 1.25rem; }

    /* ═══════════════════════════════════════════════════════
       DIVIDER
       ═══════════════════════════════════════════════════════ */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 1.5rem 0;
    }

    /* ═══════════════════════════════════════════════════════
       AVATAR
       ═══════════════════════════════════════════════════════ */
    .avatar {
        width: 48px; height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--pulse), var(--violet));
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 1.2rem; color: #fff;
        flex-shrink: 0;
        border: 2px solid var(--border);
    }
    .avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
    .avatar-lg { width: 96px; height: 96px; font-size: 2rem; }
    .avatar-sm { width: 32px; height: 32px; font-size: 0.85rem; }

    /* ═══════════════════════════════════════════════════════
       TITLE COLOR SYSTEM (matches original color names)
       ═══════════════════════════════════════════════════════ */
    .title-white  { color: #e0e8ff; }
    .title-green  { color: #22D3A5; }
    .title-blue   { color: #60A5FA; }
    .title-purple { color: #A855F7; }
    .title-yellow { color: #FFD166; text-shadow: 0 0 10px rgba(255,209,102,0.5); }
    .title-red    { color: #FF4D6D; text-shadow: 0 0 10px rgba(255,77,109,0.5); }

    /* ═══════════════════════════════════════════════════════
       QUEST / ACHIEVEMENT ITEMS
       ═══════════════════════════════════════════════════════ */
    .quest-item {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        transition: var(--transition);
    }
    .quest-item:hover { border-color: var(--border-hover); }
    .quest-item.completed { border-color: rgba(34, 211, 165, 0.35); }
    .quest-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }
    .quest-item-name { font-weight: 600; font-size: 0.9rem; }
    .quest-item-xp { font-family: var(--font-mono); font-size: 0.78rem; color: var(--gold); }
    .quest-item-desc { font-size: 0.8rem; color: var(--ink-3); margin-bottom: 0.6rem; }
    .quest-complete-badge { color: var(--green); font-size: 0.8rem; font-weight: 600; }

    /* ═══════════════════════════════════════════════════════
       ROOM / POST ITEMS
       ═══════════════════════════════════════════════════════ */
    .room-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        transition: var(--transition);
    }
    .room-card:hover { border-color: var(--border-hover); box-shadow: var(--pulse-glow); }
    .room-card-name { font-weight: 700; font-size: 1rem; color: var(--pulse); }
    .room-card-name.error { color: var(--ember); }

    .post-item {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
    }
    .post-item-meta { font-size: 0.75rem; color: var(--ink-3); font-family: var(--font-mono); margin-bottom: 0.4rem; }
    .post-item-meta strong { color: var(--pulse); }

    /* ═══════════════════════════════════════════════════════
       NOTIFICATION ITEMS
       ═══════════════════════════════════════════════════════ */
    .notif-item {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.9rem 1.1rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        transition: var(--transition);
    }
    .notif-item.unread {
        border-left: 3px solid var(--pulse);
        background: linear-gradient(90deg, var(--pulse-dim), var(--surface-2));
    }
    .notif-item-msg { font-size: 0.875rem; color: var(--ink-2); }
    .notif-item-time { font-size: 0.72rem; color: var(--ink-3); font-family: var(--font-mono); white-space: nowrap; }

    /* ═══════════════════════════════════════════════════════
       ADMIN PANEL ITEMS
       ═══════════════════════════════════════════════════════ */
    .admin-list-item {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        padding: 0.75rem 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }
    .admin-list-item + .admin-list-item { margin-top: 0.5rem; }
    .admin-list-item-title { font-size: 0.875rem; color: var(--ink-2); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* ═══════════════════════════════════════════════════════
       CATEGORY PAGE HERO STRIP
       ═══════════════════════════════════════════════════════ */
    .page-hero {
        background: linear-gradient(135deg, var(--surface-2), var(--surface));
        border-bottom: 1px solid var(--border);
        padding: 2rem 0;
        margin-bottom: 2rem;
    }
    .page-hero h1 {
        font-family: var(--font-display);
        font-size: clamp(1.6rem, 4vw, 2.4rem);
        font-weight: 900;
        color: var(--ink);
        letter-spacing: 0.02em;
    }
    .page-hero h1 span { color: var(--pulse); }
    </style>
</head>
<body>

<!-- ══════════════════════════════════════════════════════
     NAVIGATION
     ══════════════════════════════════════════════════════ -->
<nav class="nav">
    <div class="nav-inner">
        <!-- Brand -->
        <a href="/" class="brand-logo">Mi Digital Verse</a>

        <!-- Desktop Links -->
        <div class="nav-links">
            <a href="/" class="nav-link">Ana Səhifə</a>
            <a href="/news" class="nav-link">Xəbərlər</a>

            <div class="nav-dropdown">
                <button class="nav-dropdown-btn">
                    Kitabxana <span class="chevron">▾</span>
                </button>
                <div class="nav-dropdown-menu">
                    <a href="/category/anime">Anime</a>
                    <a href="/category/manga">Manga</a>
                    <a href="/category/webtoon">Webtoon</a>
                    <a href="/category/manhua">Manhua</a>
                    <a href="/category/game">Oyun</a>
                    <a href="/manga">Bütün Kitabxana</a>
                </div>
            </div>

            <a href="/community" class="nav-link">İcma</a>
            <a href="/about" class="nav-link">Haqqımızda</a>

            {% if current_user.is_authenticated %}
            <a href="/profile" class="nav-link">Profil</a>
            {% if current_user.is_admin %}
            <a href="/admin" class="nav-btn-admin">Admin</a>
            {% endif %}
            {% endif %}
        </div>

        <!-- Desktop Actions -->
        <div class="nav-actions nav-desktop-actions">
            <a href="/news" class="nav-icon-btn" title="Axtar">🔍</a>

            {% if current_user.is_authenticated %}
            <a href="/notifications" class="nav-icon-btn" title="Bildirişlər">
                🔔
                {% if unread_notifications_count > 0 %}
                <span class="nav-notif-badge">{{ unread_notifications_count }}</span>
                {% endif %}
            </a>
            <a href="/logout" class="nav-btn-logout">Çıxış</a>
            {% else %}
            <button onclick="openModal()" class="nav-btn-login">Giriş / Qeydiyyat</button>
            {% endif %}

            <!-- Theme Toggle -->
            <button id="themeToggle" class="nav-icon-btn" title="Tema dəyiş">🌙</button>
        </div>

        <!-- Mobile menu button -->
        <button class="mobile-menu-btn" id="mobileMenuBtn" aria-label="Menyu">☰</button>
    </div>
</nav>

<!-- Mobile menu -->
<div class="mobile-menu" id="mobileMenu">
    <div class="mobile-menu-top">
        <button id="themeToggleMobile" class="nav-icon-btn">🌙</button>
        {% if current_user.is_authenticated %}
        <a href="/notifications" class="nav-icon-btn" style="position:relative;">
            🔔
            {% if unread_notifications_count > 0 %}
            <span class="nav-notif-badge">{{ unread_notifications_count }}</span>
            {% endif %}
        </a>
        {% endif %}
    </div>
    <a href="/">Ana Səhifə</a>
    <a href="/news">Xəbərlər</a>
    <a href="/category/anime">Anime</a>
    <a href="/category/manga">Manga</a>
    <a href="/category/webtoon">Webtoon</a>
    <a href="/category/manhua">Manhua</a>
    <a href="/category/game">Oyun</a>
    <a href="/manga">Kitabxana</a>
    <a href="/community">İcma</a>
    <a href="/about">Haqqımızda</a>
    {% if current_user.is_authenticated %}
    <a href="/profile">Profil</a>
    {% if current_user.is_admin %}<a href="/admin">Admin</a>{% endif %}
    <a href="/logout" style="color:var(--ember)">Çıxış</a>
    {% else %}
    <button onclick="openModal(); document.getElementById('mobileMenu').classList.remove('open');" style="color:var(--pulse)">Giriş / Qeydiyyat</button>
    {% endif %}
</div>

<!-- ══════════════════════════════════════════════════════
     AUTH MODAL
     ══════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="authModal">
    <div class="modal">
        <button class="modal-close" onclick="closeModal()">✕</button>

        <div class="modal-tabs">
            <div class="modal-tab active" id="loginTabBtn" onclick="showLogin()">Giriş</div>
            <div class="modal-tab" id="registerTabBtn" onclick="showRegister()">Qeydiyyat</div>
        </div>

        <form id="loginForm" action="/login" method="POST" class="modal-form">
            <div class="form-group">
                <label class="form-label">İstifadəçi adı</label>
                <input type="text" name="username" placeholder="istifadeci_adi" required class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Şifrə</label>
                <input type="password" name="password" placeholder="••••••••" required class="form-input">
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;">Daxil ol</button>
        </form>

        <form id="registerForm" action="/register" method="POST" class="modal-form hidden">
            <div class="form-group">
                <label class="form-label">İstifadəçi adı</label>
                <input type="text" name="username" placeholder="istifadeci_adi" required class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="email" placeholder="email@nümunə.com" required class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Şifrə <span class="text-xs text-muted">(ən az 8 simvol)</span></label>
                <input type="password" name="password" placeholder="••••••••" required class="form-input">
            </div>
            <button type="submit" class="btn btn-violet" style="width:100%;justify-content:center;">Qeydiyyatdan keç</button>
        </form>
    </div>
</div>

<!-- ══════════════════════════════════════════════════════
     REPORT MODAL
     ══════════════════════════════════════════════════════ -->
<div class="report-modal-overlay" id="reportModal">
    <div class="modal">
        <button class="modal-close" onclick="closeReportModal()">✕</button>
        <h3 class="font-bold mb-4" style="font-size:1.1rem;">Şikayət et</h3>
        <form action="/report/submit" method="POST" class="modal-form">
            <input type="hidden" name="target_type" id="reportTargetType">
            <input type="hidden" name="target_id" id="reportTargetId">
            <div class="form-group">
                <label class="form-label">Səbəb</label>
                <select name="reason" class="form-select" required>
                    <option value="">Səbəb seçin</option>
                    <option value="söyüş">Söyüş</option>
                    <option value="spoiler">Spoiler paylaşır</option>
                    <option value="təhqir">Təhqir edici</option>
                    <option value="spam">Spam</option>
                    <option value="digər">Digər</option>
                </select>
            </div>
            <button type="submit" class="btn btn-ember" style="width:100%;justify-content:center;">Göndər</button>
        </form>
    </div>
</div>

<!-- ══════════════════════════════════════════════════════
     FLASH MESSAGES
     ══════════════════════════════════════════════════════ -->
<div class="flash-wrap" id="flashWrap">
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
            <div class="flash" id="flash-{{ loop.index }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
</div>

<main>{% block content %}{% endblock %}</main>

<!-- ══════════════════════════════════════════════════════
     FOOTER
     ══════════════════════════════════════════════════════ -->
<footer>
    <div class="footer-inner">
        <span class="brand-logo" style="font-size:1rem;">Mi Digital Verse</span>
        <p class="footer-copy">© {{ now.year }} Mi Digital Verse. Bütün hüquqlar qorunur.</p>
    </div>
</footer>

<!-- ══════════════════════════════════════════════════════
     JAVASCRIPT
     ══════════════════════════════════════════════════════ -->
<script>
/* ---------- THEME ---------- */
const html = document.documentElement;
function setTheme(t) {
    html.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
    const icon = t === 'light' ? '☀️' : '🌙';
    document.getElementById('themeToggle').textContent = icon;
    document.getElementById('themeToggleMobile').textContent = icon;
}
const savedTheme = localStorage.getItem('theme') || 'dark';
setTheme(savedTheme);

document.getElementById('themeToggle').addEventListener('click', () => {
    setTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});
document.getElementById('themeToggleMobile').addEventListener('click', () => {
    setTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

/* ---------- MOBILE MENU ---------- */
document.getElementById('mobileMenuBtn').addEventListener('click', () => {
    document.getElementById('mobileMenu').classList.toggle('open');
});

/* ---------- AUTH MODAL ---------- */
function openModal()   { document.getElementById('authModal').classList.add('open'); }
function closeModal()  { document.getElementById('authModal').classList.remove('open'); }
document.getElementById('authModal').addEventListener('click', e => { if (e.target === e.currentTarget) closeModal(); });

function showLogin() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('loginTabBtn').classList.add('active');
    document.getElementById('registerTabBtn').classList.remove('active');
}
function showRegister() {
    document.getElementById('registerForm').classList.remove('hidden');
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerTabBtn').classList.add('active');
    document.getElementById('loginTabBtn').classList.remove('active');
}

/* ---------- REPORT MODAL ---------- */
function openReportModal(type, id) {
    document.getElementById('reportTargetType').value = type;
    document.getElementById('reportTargetId').value = id;
    document.getElementById('reportModal').classList.add('open');
}
function closeReportModal() {
    document.getElementById('reportModal').classList.remove('open');
}
document.getElementById('reportModal').addEventListener('click', e => { if (e.target === e.currentTarget) closeReportModal(); });

/* ---------- AUTO-DISMISS FLASH ---------- */
setTimeout(() => {
    const wrap = document.getElementById('flashWrap');
    if (wrap) {
        wrap.style.transition = 'opacity 0.5s ease';
        wrap.style.opacity = '0';
        setTimeout(() => wrap.remove(), 500);
    }
}, 5000);

/* ---------- REDUCED MOTION ---------- */
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.style.setProperty('--transition', 'none');
}
</script>
</body>
</html>
"""

# ============================================================
#  Mi Digital Verse — Complete UI/UX Overhaul
#  Part 2: All remaining HTML templates + Flask routes + init
#  Picks up exactly where Part 1's BASE_HTML definition ended.
#  All user-facing strings remain in Azerbaijani.
# ============================================================

# ────────────────────────────────────────────────────────────
#  INDEX_HTML
# ────────────────────────────────────────────────────────────
INDEX_HTML = """
{% extends "base.html" %}
{% block title %}Ana Səhifə - Mi Digital Verse{% endblock %}
{% block content %}

<!-- HERO -->
<section style="
    background: linear-gradient(135deg, var(--surface-2) 0%, var(--void-3) 60%, var(--surface) 100%);
    border-bottom: 1px solid var(--border);
    padding: 4rem 0 3rem;
    position: relative;
    overflow: hidden;
">
    <!-- Decorative orb -->
    <div style="
        position: absolute; top: -80px; right: -80px;
        width: 400px; height: 400px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%);
        pointer-events: none;
    "></div>
    <div class="container" style="position:relative; text-align:center;">
        <div style="display:inline-flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
            <span class="chip chip-pulse">Anime · Manga · Webtoon</span>
        </div>
        <h1 style="
            font-family: var(--font-display);
            font-size: clamp(2rem, 5vw, 3.2rem);
            font-weight: 900;
            color: var(--ink);
            letter-spacing: 0.02em;
            margin-bottom: 0.75rem;
            line-height: 1.1;
        ">
            Xoş <span style="color:var(--pulse); text-shadow: 0 0 30px rgba(0,212,255,0.5);">gəldiniz</span>
        </h1>
        <p style="color: var(--ink-3); font-size: 1.05rem; max-width: 520px; margin: 0 auto 2rem;">
            Anime, manhwa, manhua və oyun dünyasının ən son xəbərləri bir yerdə.
        </p>
        <div style="display:flex; justify-content:center; gap:1rem; flex-wrap:wrap;">
            <a href="/news" class="btn btn-primary btn-lg">Xəbərləri kəşf et</a>
            <a href="/manga" class="btn btn-ghost btn-lg">Kitabxanaya bax</a>
        </div>
    </div>
</section>

<div class="container page-content">
    <div class="layout-main-sidebar">

        <!-- MAIN COLUMN -->
        <div>
            <!-- Latest News -->
            <div class="section-heading">
                <span class="section-heading-dot"></span>
                <h2>Son Xəbərlər</h2>
                <div class="section-heading-line"></div>
                <a href="/news" class="btn btn-ghost btn-sm">Hamısı →</a>
            </div>

            <div class="space-y-lg">
                {% for news in latest_news %}
                <a href="/news/{{ news.id }}" class="news-card" style="display:flex; flex-direction:column;">
                    {% if news.image_url %}
                    <div style="height:200px; overflow:hidden; border-radius:var(--radius-lg) var(--radius-lg) 0 0;">
                        <img src="{{ news.image_url }}" alt="{{ news.title }}"
                             style="width:100%; height:100%; object-fit:cover; transition:transform 0.4s ease;"
                             onmouseover="this.style.transform='scale(1.04)'"
                             onmouseout="this.style.transform='scale(1)'">
                    </div>
                    {% endif %}
                    <div class="news-card-body">
                        <div class="news-card-category">{{ news.category }}</div>
                        <div class="news-card-title">{{ news.title }}</div>
                        <div class="news-card-meta">
                            <span>📅 {{ news.published_at.strftime('%d.%m.%Y') }}</span>
                            <span>👁 {{ news.views }}</span>
                            <span>❤ {{ news.likes }}</span>
                        </div>
                    </div>
                </a>
                {% else %}
                <div class="card card-inner" style="text-align:center; color:var(--ink-3); padding:3rem;">
                    Hələ xəbər yoxdur.
                </div>
                {% endfor %}
            </div>

            <!-- Most Read -->
            <div class="section-heading mt-8">
                <span class="section-heading-dot" style="background:var(--gold); box-shadow:0 0 8px var(--gold);"></span>
                <h2>Ən Çox Oxunanlar</h2>
                <div class="section-heading-line"></div>
            </div>
            <div class="space-y">
                {% for news in most_read %}
                <a href="/news/{{ news.id }}" class="news-card"
                   style="display:flex; flex-direction:row; align-items:center; gap:1rem; padding:0.75rem 1rem;">
                    <span style="
                        font-family: var(--font-mono);
                        font-size: 1.5rem;
                        font-weight: 900;
                        color: var(--ink-muted);
                        min-width: 2rem;
                        text-align:center;
                    ">{{ loop.index }}</span>
                    <div style="flex:1; min-width:0;">
                        <div class="news-card-title" style="font-size:0.9rem;">{{ news.title }}</div>
                        <div class="news-card-meta">
                            <span>👁 {{ news.views }} oxunma</span>
                        </div>
                    </div>
                </a>
                {% endfor %}
            </div>
        </div>

        <!-- SIDEBAR -->
        <aside>
            <div class="section-heading">
                <span class="section-heading-dot" style="background:var(--violet); box-shadow:0 0 8px var(--violet);"></span>
                <h2>Seçilmiş</h2>
                <div class="section-heading-line"></div>
            </div>
            <div class="space-y">
                {% for m in featured %}
                <a href="/manga/{{ m.id }}" class="card" style="
                    display:flex; align-items:center; gap:0.9rem;
                    padding:0.75rem;
                    border-radius:var(--radius-md);
                ">
                    <img src="{{ m.cover_url }}" alt="{{ m.title }}"
                         style="width:52px; height:75px; object-fit:cover; border-radius:var(--radius-sm); flex-shrink:0;">
                    <div style="min-width:0;">
                        <div style="font-weight:700; font-size:0.875rem; color:var(--ink);
                                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {{ m.title }}
                        </div>
                        <div style="font-size:0.72rem; color:var(--ink-3); font-family:var(--font-mono);">
                            {{ m.type | capitalize }}
                        </div>
                        <div class="manga-card-rating">⭐ {{ m.rating }}</div>
                    </div>
                </a>
                {% endfor %}
            </div>

            <!-- Category quick-links -->
            <div class="section-heading mt-6">
                <span class="section-heading-dot" style="background:var(--ember); box-shadow:0 0 8px var(--ember);"></span>
                <h2>Kateqoriyalar</h2>
                <div class="section-heading-line"></div>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.4rem;">
                {% for cat, icon in [('anime','🎌'),('manga','📖'),('webtoon','📱'),('manhua','🐉'),('game','🎮')] %}
                <a href="/category/{{ cat }}" class="btn btn-secondary" style="justify-content:flex-start; gap:0.6rem;">
                    <span>{{ icon }}</span> {{ cat | capitalize }}
                </a>
                {% endfor %}
            </div>
        </aside>

    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  NEWS_LIST_HTML
# ────────────────────────────────────────────────────────────
NEWS_LIST_HTML = """
{% extends "base.html" %}
{% block title %}Xəbərlər - Mi Digital Verse{% endblock %}
{% block content %}

<div class="page-hero">
    <div class="container">
        <h1>📰 <span>Xəbərlər</span></h1>
        <p style="color:var(--ink-3); margin-top:0.4rem;">Ən son anime, manga və oyun dünyası xəbərləri</p>
    </div>
</div>

<div class="container" style="padding-bottom:4rem;">
    <!-- Search bar -->
    <form action="/search" method="GET" style="display:flex; gap:0.75rem; margin-bottom:2rem;">
        <input type="text" name="q" placeholder="Xəbər axtar..." class="form-input" style="flex:1;">
        <button type="submit" class="btn btn-primary">🔍 Axtar</button>
    </form>

    <!-- Category filter chips -->
    <div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:2rem;">
        <a href="/news" class="chip chip-pulse">Hamısı</a>
        {% for cat in ['Anime','Manga','Webtoon','Manhua','Oyun','Ümumi'] %}
        <a href="/category/{{ cat | lower }}" class="chip chip-violet">{{ cat }}</a>
        {% endfor %}
    </div>

    <div class="grid-2">
        {% for news in all_news %}
        <a href="/news/{{ news.id }}" class="news-card">
            {% if news.image_url %}
            <div style="height:180px; overflow:hidden;">
                <img src="{{ news.image_url }}" alt="{{ news.title }}"
                     style="width:100%; height:100%; object-fit:cover;">
            </div>
            {% endif %}
            <div class="news-card-body">
                <div class="news-card-category">{{ news.category }}</div>
                <div class="news-card-title">{{ news.title }}</div>
                <p style="font-size:0.8rem; color:var(--ink-3); margin-bottom:0.6rem;
                           display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
                    {{ news.content[:140] }}…
                </p>
                <div class="news-card-meta">
                    <span>📅 {{ news.published_at.strftime('%d.%m.%Y') }}</span>
                    <span>👁 {{ news.views }}</span>
                    <span>❤ {{ news.likes }}</span>
                </div>
            </div>
        </a>
        {% else %}
        <div class="card card-inner col-span-2" style="text-align:center; color:var(--ink-3); padding:3rem;">
            Hələ xəbər yoxdur.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  NEWS_DETAIL_HTML
# ────────────────────────────────────────────────────────────
NEWS_DETAIL_HTML = """
{% extends "base.html" %}
{% block title %}{{ news.title }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:820px; padding-top:2.5rem; padding-bottom:4rem;">

    <!-- Breadcrumb -->
    <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.78rem;
                color:var(--ink-3); font-family:var(--font-mono); margin-bottom:1.5rem;">
        <a href="/" style="color:var(--pulse);">Ana Səhifə</a>
        <span>/</span>
        <a href="/news" style="color:var(--pulse);">Xəbərlər</a>
        <span>/</span>
        <span>{{ news.category }}</span>
    </div>

    <!-- Category chip + title -->
    <div class="chip chip-pulse" style="margin-bottom:1rem;">{{ news.category }}</div>
    <h1 style="font-size:clamp(1.5rem,4vw,2.2rem); font-weight:900; color:var(--ink);
               line-height:1.2; margin-bottom:1rem;">
        {{ news.title }}
    </h1>

    <!-- Meta row -->
    <div style="display:flex; align-items:center; gap:1.25rem; flex-wrap:wrap;
                font-size:0.78rem; color:var(--ink-3); font-family:var(--font-mono); margin-bottom:1.5rem;">
        <span>📅 {{ news.published_at.strftime('%d.%m.%Y %H:%M') }}</span>
        <span>👁 {{ news.views }} oxunma</span>
        <span>❤ {{ news.likes }} bəyənmə</span>
    </div>

    <!-- Hero image -->
    {% if news.image_url %}
    <div style="border-radius:var(--radius-lg); overflow:hidden; margin-bottom:2rem;
                border:1px solid var(--border);">
        <img src="{{ news.image_url }}" alt="{{ news.title }}"
             style="width:100%; max-height:440px; object-fit:contain; background:var(--surface-2);">
    </div>
    {% endif %}

    <!-- Main content -->
    <div style="font-size:1.05rem; line-height:1.85; color:var(--ink-2);
                white-space:pre-line;" class="article-body">
        {{ news.content }}
    </div>

    <!-- Content blocks -->
    {% for block in news.blocks %}
    <div style="margin-top:2rem;">
        {% if block.block_type == 'text' %}
        <div style="font-size:1rem; line-height:1.8; color:var(--ink-2); white-space:pre-line;">
            {{ block.text_content }}
        </div>
        {% elif block.block_type == 'image' and block.image_url %}
        <div style="border-radius:var(--radius-md); overflow:hidden; border:1px solid var(--border);">
            <img src="{{ block.image_url }}" alt="Məzmun şəkli"
                 style="width:100%; max-height:420px; object-fit:contain; background:var(--surface-2);">
        </div>
        {% endif %}
    </div>
    {% endfor %}

    <!-- Divider -->
    <div class="divider" style="margin-top:2.5rem;"></div>

    <!-- Action row -->
    <div style="display:flex; flex-wrap:wrap; gap:0.75rem; align-items:center;">
        {% if current_user.is_authenticated %}
        <form action="/like-news/{{ news.id }}" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-ember">
                ❤ Bəyən ({{ news.likes }})
            </button>
        </form>
        {% else %}
        <span class="btn btn-secondary">❤ {{ news.likes }} bəyənmə</span>
        {% endif %}
        <a href="/create-room?news_id={{ news.id }}" class="btn btn-violet">
            💬 Bu xəbəri müzakirə et
        </a>
        <a href="/news" class="btn btn-ghost">← Geri</a>
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  MANGA_LIST_HTML
# ────────────────────────────────────────────────────────────
MANGA_LIST_HTML = """
{% extends "base.html" %}
{% block title %}Kitabxana - Mi Digital Verse{% endblock %}
{% block content %}

<div class="page-hero">
    <div class="container">
        <h1>📚 <span>Kitabxana</span></h1>
        <p style="color:var(--ink-3); margin-top:0.4rem;">
            Anime, Manga, Manhwa, Manhua və Webtoon kolleksiyası
        </p>
    </div>
</div>

<div class="container" style="padding-bottom:4rem;">
    <!-- Filter form -->
    <form action="/manga" method="GET"
          style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:2rem; align-items:flex-end;">
        <div style="flex:1; min-width:200px;">
            <input type="text" name="q" placeholder="Başlıq axtar..."
                   class="form-input" value="{{ request.args.get('q','') }}">
        </div>
        <div>
            <select name="type" class="form-select" style="min-width:140px;">
                <option value="">Hamısı</option>
                {% for t in ['anime','manga','manhwa','manhua','webtoon'] %}
                <option value="{{ t }}" {% if request.args.get('type') == t %}selected{% endif %}>
                    {{ t | capitalize }}
                </option>
                {% endfor %}
            </select>
        </div>
        <button type="submit" class="btn btn-primary">🔍 Axtar</button>
    </form>

    <!-- Type filter chips -->
    <div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:2rem;">
        <a href="/manga" class="chip chip-pulse">Hamısı</a>
        {% for t,icon in [('anime','🎌'),('manga','📖'),('manhwa','🇰🇷'),('manhua','🐉'),('webtoon','📱')] %}
        <a href="/manga?type={{ t }}" class="chip chip-violet">{{ icon }} {{ t | capitalize }}</a>
        {% endfor %}
    </div>

    <div class="grid-4">
        {% for m in mangas %}
        <a href="/manga/{{ m.id }}" class="manga-card" style="position:relative;">
            <div class="manga-card-badge">
                <span class="chip chip-pulse" style="font-size:0.62rem;">{{ m.type }}</span>
            </div>
            <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="manga-card-img">
            <div class="manga-card-body">
                <div class="manga-card-title">{{ m.title }}</div>
                <div class="manga-card-sub">{{ m.status }} · {{ m.chapters }} böl.</div>
                <div class="manga-card-rating">⭐ {{ m.rating }}</div>
            </div>
        </a>
        {% else %}
        <div class="card card-inner"
             style="grid-column:1/-1; text-align:center; color:var(--ink-3); padding:3rem;">
            Heç nə tapılmadı.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  MANGA_DETAIL_HTML
# ────────────────────────────────────────────────────────────
MANGA_DETAIL_HTML = """
{% extends "base.html" %}
{% block title %}{{ manga.title }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:900px; padding-top:2.5rem; padding-bottom:4rem;">

    <!-- Breadcrumb -->
    <div style="display:flex; align-items:center; gap:0.5rem; font-size:0.78rem;
                color:var(--ink-3); font-family:var(--font-mono); margin-bottom:1.5rem;">
        <a href="/manga" style="color:var(--pulse);">Kitabxana</a>
        <span>/</span>
        <a href="/manga?type={{ manga.type }}" style="color:var(--pulse);">{{ manga.type | capitalize }}</a>
        <span>/</span>
        <span>{{ manga.title }}</span>
    </div>

    <div style="display:grid; grid-template-columns:220px 1fr; gap:2rem; align-items:start;">
        <!-- Cover -->
        <div>
            <div style="border-radius:var(--radius-md); overflow:hidden; border:1px solid var(--border);
                        box-shadow:0 8px 32px rgba(0,0,0,0.4);">
                <img src="{{ manga.cover_url }}" alt="{{ manga.title }}"
                     style="width:100%; aspect-ratio:2/3; object-fit:cover;">
            </div>
            <!-- Action buttons -->
            <div style="margin-top:1rem; display:flex; flex-direction:column; gap:0.5rem;">
                {% if current_user.is_authenticated %}
                <form action="/like-manga/{{ manga.id }}" method="POST">
                    <button type="submit" class="btn btn-ember w-full" style="justify-content:center;">
                        ❤ Bəyən ({{ manga.likes }})
                    </button>
                </form>
                {% else %}
                <div class="btn btn-secondary" style="justify-content:center;">❤ {{ manga.likes }}</div>
                {% endif %}
                <a href="/community" class="btn btn-violet" style="justify-content:center;">
                    💬 Müzakirə
                </a>
            </div>
        </div>

        <!-- Details -->
        <div>
            <div class="chip chip-pulse" style="margin-bottom:0.75rem;">{{ manga.type | capitalize }}</div>
            <h1 style="font-size:clamp(1.4rem,3.5vw,2rem); font-weight:900; color:var(--ink);
                       margin-bottom:1rem; line-height:1.2;">
                {{ manga.title }}
            </h1>

            <!-- Stats grid -->
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:0.75rem; margin-bottom:1.5rem;">
                {% for label, val, color in [
                    ('Reytinq', '⭐ ' ~ manga.rating, 'var(--gold)'),
                    ('Status', manga.status, 'var(--green)'),
                    ('Bölüm', manga.chapters ~ ' böl.', 'var(--pulse)')
                ] %}
                <div style="background:var(--surface-2); border:1px solid var(--border);
                            border-radius:var(--radius-sm); padding:0.75rem; text-align:center;">
                    <div style="font-family:var(--font-mono); font-size:1rem;
                                font-weight:700; color:{{ color }};">{{ val }}</div>
                    <div style="font-size:0.7rem; color:var(--ink-3); margin-top:0.2rem;">{{ label }}</div>
                </div>
                {% endfor %}
            </div>

            <div style="font-size:0.975rem; line-height:1.8; color:var(--ink-2);">
                {{ manga.description }}
            </div>

            <!-- View count -->
            <div style="margin-top:1rem; font-size:0.78rem;
                        color:var(--ink-3); font-family:var(--font-mono);">
                👁 {{ manga.views }} oxunma
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  COMMUNITY_HTML
# ────────────────────────────────────────────────────────────
COMMUNITY_HTML = """
{% extends "base.html" %}
{% block title %}İcma - Mi Digital Verse{% endblock %}
{% block content %}

<div class="page-hero">
    <div class="container">
        <h1>💬 <span>İcma</span></h1>
        <p style="color:var(--ink-3); margin-top:0.4rem;">
            Müzakirə otaqları yarat, fikir paylaş.
        </p>
    </div>
</div>

<div class="container" style="padding-bottom:4rem;">

    <!-- Create room panel -->
    {% if current_user.is_authenticated %}
    <div class="card card-inner mb-6">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
            + Yeni Müzakirə Otağı
        </h2>
        <form action="/create-room" method="POST"
              style="display:grid; grid-template-columns:1fr 1fr auto; gap:0.75rem; align-items:end;">
            <div class="form-group">
                <label class="form-label">Otaq adı</label>
                <input type="text" name="room_name" placeholder="Otaq adını daxil edin..."
                       required class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Xəbər seç (istəyə bağlı)</label>
                <select name="news_id" class="form-select">
                    <option value="">—</option>
                    {% for n in all_news %}
                    <option value="{{ n.id }}">{{ n.title[:50] }}{% if n.title|length > 50 %}…{% endif %}</option>
                    {% endfor %}
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Yarat</button>
        </form>
    </div>
    {% else %}
    <div class="card card-inner mb-6" style="text-align:center; padding:2rem;">
        <p style="color:var(--ink-3);">
            Otaq yaratmaq üçün
            <button onclick="openModal()" style="color:var(--pulse); font-weight:700; background:none; border:none; cursor:pointer;">
                giriş edin
            </button>.
        </p>
    </div>
    {% endif %}

    <!-- Room grid -->
    <div class="grid-3">
        {% for room in rooms %}
        <div class="room-card">
            <div class="room-card-name {% if room.name == 'Xəta Otağı' %}error{% endif %}">
                {% if room.name == 'Xəta Otağı' %}⚠{% else %}🗨{% endif %}
                {{ room.name }}
            </div>
            <div style="font-size:0.75rem; color:var(--ink-3); font-family:var(--font-mono);">
                👤 {{ room.creator.username }}
            </div>
            {% if room.news %}
            <div style="font-size:0.72rem; color:var(--ink-3); font-family:var(--font-mono);">
                📰 {{ room.news.title[:40] }}{% if room.news.title|length > 40 %}…{% endif %}
            </div>
            {% endif %}
            <div style="margin-top:auto; padding-top:0.75rem; display:flex; flex-wrap:wrap; gap:0.5rem;">
                <a href="/room/{{ room.id }}" class="btn btn-primary btn-sm">Daxil ol</a>
                <button onclick="openReportModal('room', {{ room.id }})"
                        class="btn btn-secondary btn-sm">Şikayət</button>
                {% if current_user.is_authenticated and current_user.is_admin %}
                    {% if room.name == 'Xəta Otağı' %}
                    <a href="/admin/clear-room-messages/{{ room.id }}"
                       class="btn btn-gold btn-sm"
                       onclick="return confirm('Bütün mesajları silmək istədiyinizə əminsiniz?')">Təmizlə</a>
                    {% else %}
                    <a href="/admin/delete-room/{{ room.id }}"
                       class="btn btn-danger btn-sm"
                       onclick="return confirm('Otağı silmək istədiyinizə əminsiniz?')">Sil</a>
                    {% endif %}
                {% endif %}
            </div>
        </div>
        {% else %}
        <div class="card card-inner" style="grid-column:1/-1; text-align:center; color:var(--ink-3); padding:3rem;">
            Hələ otaq yoxdur.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  ROOM_HTML
# ────────────────────────────────────────────────────────────
ROOM_HTML = """
{% extends "base.html" %}
{% block title %}{{ room.name }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:820px; padding-top:2.5rem; padding-bottom:4rem;">

    <!-- Header -->
    <div style="display:flex; align-items:center; justify-content:space-between;
                flex-wrap:wrap; gap:1rem; margin-bottom:2rem;">
        <div>
            <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink);">
                {% if room.name == 'Xəta Otağı' %}
                <span style="color:var(--ember);">⚠ {{ room.name }}</span>
                {% else %}
                🗨 {{ room.name }}
                {% endif %}
            </h1>
            <div style="font-size:0.75rem; color:var(--ink-3); font-family:var(--font-mono); margin-top:0.25rem;">
                Yaradıcı: {{ room.creator.username }}
                {% if room.news %} · 📰 {{ room.news.title[:50] }}{% endif %}
            </div>
        </div>
        <a href="/community" class="btn btn-ghost btn-sm">← İcmaya qayıt</a>
    </div>

    <!-- Compose box -->
    {% if current_user.is_authenticated %}
    <div class="card card-inner mb-6">
        <form action="/post/{{ room.id }}" method="POST">
            <div class="form-group" style="margin-bottom:0.75rem;">
                <textarea name="content" rows="3" required
                          placeholder="Mesajınızı yazın..."
                          class="form-textarea"></textarea>
            </div>
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.75rem;">
                <label style="display:flex; align-items:center; gap:0.5rem; font-size:0.85rem; color:var(--ink-3); cursor:pointer;">
                    <input type="checkbox" name="is_spoiler" value="1"
                           style="accent-color:var(--ember);"> Spoiler olaraq işarələ
                </label>
                <button type="submit" class="btn btn-primary">Göndər →</button>
            </div>
        </form>
    </div>
    {% else %}
    <div class="card card-inner mb-6" style="text-align:center; padding:1.5rem;">
        <p style="color:var(--ink-3);">
            Yazmaq üçün
            <button onclick="openModal()" style="color:var(--pulse); font-weight:700; background:none; border:none; cursor:pointer;">
                giriş edin
            </button>.
        </p>
    </div>
    {% endif %}

    <!-- Posts -->
    <div class="space-y">
        {% for post in posts %}
        <div class="post-item">
            <div class="post-item-meta">
                <strong>
                    <a href="/user/{{ post.user.username }}" style="color:var(--pulse); text-decoration:none;">
                        {{ post.user.username }}
                    </a>
                </strong>
                {% if post.user.title %}
                · <span style="color:{{ post.user.title.color }};">{{ post.user.title.name }}</span>
                {% endif %}
                · {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}
            </div>

            {% if post.is_spoiler %}
            <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ post.content }}</span>
            {% else %}
            <p style="color:var(--ink-2); font-size:0.9rem; line-height:1.7;">{{ post.content }}</p>
            {% endif %}

            <div style="display:flex; gap:0.5rem; margin-top:0.6rem; flex-wrap:wrap;">
                <button onclick="openReportModal('post', {{ post.id }})"
                        class="btn btn-secondary btn-sm">🚩 Şikayət</button>
                {% if current_user.is_authenticated and current_user.is_admin %}
                <a href="/admin/delete-post/{{ post.id }}" class="btn btn-danger btn-sm">Sil</a>
                {% endif %}
            </div>
        </div>
        {% else %}
        <div class="card card-inner" style="text-align:center; color:var(--ink-3); padding:3rem;">
            Hələ mesaj yoxdur. İlk siz yazın!
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  PROFILE_HTML
# ────────────────────────────────────────────────────────────
PROFILE_HTML = """
{% extends "base.html" %}
{% block title %}Profil - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:900px; padding-top:2.5rem; padding-bottom:4rem;">

    <!-- Profile header card -->
    <div class="card card-inner-lg mb-6" style="
        background: linear-gradient(135deg, var(--surface-2), var(--surface));
        border-color: var(--border-hover);
        position: relative; overflow: hidden;
    ">
        <!-- decorative glow -->
        <div style="position:absolute; top:-40px; right:-40px; width:200px; height:200px;
                    border-radius:50%; background:radial-gradient(circle, var(--pulse-dim) 0%, transparent 70%);
                    pointer-events:none;"></div>

        <div style="display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap; position:relative;">
            <!-- Avatar -->
            <div class="avatar avatar-lg">
                {% if current_user.avatar %}
                <img src="{{ url_for('static', filename='uploads/' ~ current_user.avatar) }}"
                     alt="Avatar">
                {% else %}
                {{ current_user.username[0].upper() }}
                {% endif %}
            </div>

            <!-- User info -->
            <div style="flex:1; min-width:0;">
                <h1 style="font-size:1.7rem; font-weight:900; color:var(--ink); margin-bottom:0.2rem;">
                    {{ current_user.username }}
                </h1>
                {% if current_user.title %}
                <div style="margin-bottom:0.4rem;">
                    <span style="font-weight:700; color:{{ current_user.title.color }};
                                 font-family:var(--font-mono); font-size:0.85rem;">
                        ✦ {{ current_user.title.name }}
                    </span>
                </div>
                {% endif %}
                <div style="display:flex; flex-wrap:wrap; gap:1rem;
                            font-size:0.78rem; color:var(--ink-3); font-family:var(--font-mono);">
                    <span>Səviyyə <strong style="color:var(--pulse);">{{ current_user.get_level() }}</strong></span>
                    <span>{{ current_user.points }} XP</span>
                    <span>🔥 {{ current_user.streak }} gün seriya</span>
                    <span>📧 {{ current_user.email }}</span>
                </div>

                <!-- XP progress bar -->
                <div style="margin-top:0.75rem;">
                    <div style="display:flex; justify-content:space-between;
                                font-size:0.72rem; color:var(--ink-3); font-family:var(--font-mono);
                                margin-bottom:0.3rem;">
                        <span>{{ current_user.points }} XP</span>
                        <span>Sonraki səviyyə: {{ current_user.get_next_level_xp() }} XP</span>
                    </div>
                    <div class="xp-bar-track">
                        <div class="xp-bar-fill" style="width:{{ current_user.get_level_progress() }}%;"></div>
                    </div>
                </div>
            </div>

            <!-- Daily reward -->
            <div style="flex-shrink:0; text-align:center;">
                {% if not claimed_today %}
                <form action="/claim-daily" method="POST">
                    <button type="submit" class="btn btn-green btn-lg">
                        🎁 Günlük Ödül
                    </button>
                </form>
                {% else %}
                <div class="chip chip-green">✔ Bu gün alındı</div>
                {% endif %}
            </div>
        </div>

        <!-- Showcase titles -->
        {% if current_user.showcase1_id or current_user.showcase2_id or current_user.showcase3_id %}
        <div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-top:1.25rem; padding-top:1.25rem;
                    border-top:1px solid var(--border);">
            {% for sid in [current_user.showcase1_id, current_user.showcase2_id, current_user.showcase3_id] %}
            {% if sid %}
            {% set st = earned_titles | selectattr('title.id', 'equalto', sid) | first %}
            {% if st %}
            <span style="font-family:var(--font-mono); font-size:0.78rem; font-weight:700;
                         color:{{ st.title.color }}; background:var(--surface-3);
                         border:1px solid var(--border); border-radius:100px; padding:0.25rem 0.75rem;">
                ✦ {{ st.title.name }}
            </span>
            {% endif %}
            {% endif %}
            {% endfor %}
        </div>
        {% endif %}
    </div>

    <!-- Two-column layout: left (settings) / right (gamification) -->
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">

        <!-- LEFT: Settings -->
        <div style="display:flex; flex-direction:column; gap:1.5rem;">

            <!-- Avatar upload -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                    🖼 Profil Şəkli
                </h2>
                <form action="/upload-avatar" method="POST" enctype="multipart/form-data"
                      style="display:flex; flex-direction:column; gap:0.75rem;">
                    <input type="file" name="avatar" accept="image/*" class="form-input"
                           style="padding:0.4rem;">
                    <button type="submit" class="btn btn-violet">Yüklə</button>
                </form>
            </div>

            <!-- Bio + Social -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                    ✏ Bio və Sosial Keçidlər
                </h2>
                <form action="/profile/update-bio" method="POST"
                      style="display:flex; flex-direction:column; gap:0.85rem;">
                    <div class="form-group">
                        <label class="form-label">Bio</label>
                        <textarea name="bio" rows="3" class="form-textarea">{{ current_user.bio or '' }}</textarea>
                    </div>
                    {% for name, field, placeholder in [
                        ('Twitter', 'twitter_link', 'https://twitter.com/…'),
                        ('Instagram', 'instagram_link', 'https://instagram.com/…'),
                        ('Discord', 'discord_link', 'https://discord.gg/…')
                    ] %}
                    <div class="form-group">
                        <label class="form-label">{{ name }}</label>
                        <input type="text" name="{{ field }}" class="form-input"
                               placeholder="{{ placeholder }}"
                               value="{{ current_user[field] or '' if current_user[field] is defined else '' }}">
                    </div>
                    {% endfor %}
                    <button type="submit" class="btn btn-primary">Yadda saxla</button>
                </form>
            </div>

            <!-- Password -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                    🔒 Şifrəni Dəyiş
                </h2>
                <form action="/profile/change-password" method="POST"
                      style="display:flex; flex-direction:column; gap:0.85rem;">
                    <div class="form-group">
                        <label class="form-label">Hazırkı Şifrə</label>
                        <input type="password" name="current_password" required class="form-input" placeholder="••••••••">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Yeni Şifrə</label>
                        <input type="password" name="new_password" required class="form-input" placeholder="••••••••">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Yeni Şifrəni Təkrar</label>
                        <input type="password" name="confirm_password" required class="form-input" placeholder="••••••••">
                    </div>
                    <button type="submit" class="btn btn-primary">Yenilə</button>
                </form>
            </div>
        </div>

        <!-- RIGHT: Gamification -->
        <div style="display:flex; flex-direction:column; gap:1.5rem;">

            <!-- Earned Titles -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--gold);">
                    🏅 Qazanılmış Ünvanlar
                </h2>
                {% if earned_titles %}
                <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:0.6rem;">
                    {% for ut in earned_titles %}
                    <div style="background:var(--surface-2); border:1px solid var(--border);
                                border-radius:var(--radius-sm); padding:0.6rem; text-align:center;">
                        <div style="font-weight:700; font-size:0.82rem; color:{{ ut.title.color }};
                                    font-family:var(--font-mono);">
                            ✦ {{ ut.title.name }}
                        </div>
                        <div style="font-size:0.68rem; color:var(--ink-3); margin:0.3rem 0;">
                            {{ ut.title.description[:40] }}{% if ut.title.description|length > 40 %}…{% endif %}
                        </div>
                        <form action="/profile/set-active-title/{{ ut.title.id }}" method="POST">
                            <button type="submit" class="btn btn-ghost btn-sm"
                                    style="font-size:0.68rem; padding:0.2rem 0.5rem;">
                                Aktiv et
                            </button>
                        </form>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p style="color:var(--ink-3); font-size:0.85rem;">Hələ ünvan yoxdur.</p>
                {% endif %}
            </div>

            <!-- Showcase setter -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--violet);">
                    🖼 Vitrin (3 ünvan)
                </h2>
                <form action="/profile/set-showcase" method="POST"
                      style="display:flex; flex-direction:column; gap:0.75rem;">
                    {% for i in range(1,4) %}
                    <div class="form-group">
                        <label class="form-label">Vitrin {{ i }}</label>
                        <select name="showcase{{ i }}" class="form-select">
                            <option value="">— Boş —</option>
                            {% for ut in earned_titles %}
                            <option value="{{ ut.title.id }}"
                                {% if (i==1 and current_user.showcase1_id == ut.title.id)
                                    or (i==2 and current_user.showcase2_id == ut.title.id)
                                    or (i==3 and current_user.showcase3_id == ut.title.id) %}
                                selected{% endif %}>
                                {{ ut.title.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    {% endfor %}
                    <button type="submit" class="btn btn-violet">Vitrinini yadda saxla</button>
                </form>
            </div>

            <!-- Daily Quests -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                    📋 Gündəlik Görəvlər
                </h2>
                <div class="space-y">
                    {% for quest in daily_quests %}
                    {% set progress = user_quests.get(quest.id) %}
                    <div class="quest-item {% if progress and progress.completed %}completed{% endif %}">
                        <div class="quest-item-header">
                            <span class="quest-item-name">{{ quest.name }}</span>
                            <span class="quest-item-xp">+{{ quest.reward_xp }} XP</span>
                        </div>
                        <div class="quest-item-desc">{{ quest.description }}</div>
                        {% if progress and progress.completed %}
                        <div class="quest-complete-badge">✔ Tamamlandı</div>
                        {% else %}
                        <div class="xp-bar-track" style="height:4px;">
                            <div class="xp-bar-fill"
                                 style="width:{{ ((progress.progress / quest.target_value) * 100) if progress else 0 }}%;"></div>
                        </div>
                        <div style="font-size:0.68rem; color:var(--ink-3); font-family:var(--font-mono); margin-top:0.3rem;">
                            {{ progress.progress if progress else 0 }} / {{ quest.target_value }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Weekly Quests -->
            <div class="card card-inner">
                <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                    📅 Həftəlik Görəvlər
                </h2>
                <div class="space-y">
                    {% for quest in weekly_quests %}
                    {% set progress = user_quests.get(quest.id) %}
                    <div class="quest-item {% if progress and progress.completed %}completed{% endif %}">
                        <div class="quest-item-header">
                            <span class="quest-item-name">{{ quest.name }}</span>
                            <span class="quest-item-xp">+{{ quest.reward_xp }} XP</span>
                        </div>
                        <div class="quest-item-desc">{{ quest.description }}</div>
                        {% if progress and progress.completed %}
                        <div class="quest-complete-badge">✔ Tamamlandı</div>
                        {% else %}
                        <div class="xp-bar-track" style="height:4px;">
                            <div class="xp-bar-fill"
                                 style="width:{{ ((progress.progress / quest.target_value) * 100) if progress else 0 }}%;"></div>
                        </div>
                        <div style="font-size:0.68rem; color:var(--ink-3); font-family:var(--font-mono); margin-top:0.3rem;">
                            {{ progress.progress if progress else 0 }} / {{ quest.target_value }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>

        </div>
    </div>

    <!-- Achievements — full width -->
    <div class="card card-inner mt-6">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--gold);">
            🏆 Nailiyyətlər
        </h2>
        <div class="grid-2">
            {% for ach in all_achievements %}
            <div style="
                background: var(--surface-2);
                border: 1px solid {% if earned_achievements[ach.id] %}rgba(34,211,165,0.35){% else %}var(--border){% endif %};
                border-radius: var(--radius-md);
                padding: 1rem;
                display: flex;
                align-items: center;
                gap: 0.9rem;
                opacity: {% if ach.hidden and not earned_achievements[ach.id] %}0.45{% else %}1{% endif %};
                transition: var(--transition);
            ">
                <div style="font-size:1.75rem; line-height:1;">{{ ach.badge_icon }}</div>
                <div>
                    <div style="font-weight:700; font-size:0.875rem; color:var(--ink);">{{ ach.name }}</div>
                    <div style="font-size:0.75rem; color:var(--ink-3);">{{ ach.description }}</div>
                    {% if earned_achievements[ach.id] %}
                    <div style="color:var(--green); font-size:0.75rem; font-weight:600; margin-top:0.2rem;">
                        ✔ Qazanılıb
                    </div>
                    {% else %}
                    <div style="color:var(--ink-muted); font-size:0.72rem; margin-top:0.2rem;">
                        Hələ qazanılmayıb
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  USER_PROFILE_HTML  (public view)
# ────────────────────────────────────────────────────────────
USER_PROFILE_HTML = """
{% extends "base.html" %}
{% block title %}{{ profile_user.username }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:720px; padding-top:2.5rem; padding-bottom:4rem;">

    <div class="card card-inner-lg mb-6" style="
        background: linear-gradient(135deg, var(--surface-2), var(--surface));
        border-color: var(--border-hover);
        position:relative; overflow:hidden;
    ">
        <div style="position:absolute; top:-40px; right:-40px; width:200px; height:200px;
                    border-radius:50%; background:radial-gradient(circle, var(--pulse-dim) 0%, transparent 70%);
                    pointer-events:none;"></div>

        <div style="display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap;">
            <div class="avatar avatar-lg">
                {% if profile_user.avatar %}
                <img src="{{ url_for('static', filename='uploads/' ~ profile_user.avatar) }}" alt="Avatar">
                {% else %}
                {{ profile_user.username[0].upper() }}
                {% endif %}
            </div>

            <div style="flex:1; min-width:0;">
                <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink); margin-bottom:0.25rem;">
                    {{ profile_user.username }}
                </h1>
                {% if profile_user.title %}
                <div style="font-family:var(--font-mono); font-size:0.85rem;
                            color:{{ profile_user.title.color }}; font-weight:700; margin-bottom:0.4rem;">
                    ✦ {{ profile_user.title.name }}
                </div>
                {% endif %}

                <div style="display:flex; flex-wrap:wrap; gap:1rem;
                            font-size:0.78rem; color:var(--ink-3); font-family:var(--font-mono);">
                    <span>Səviyyə <strong style="color:var(--pulse);">{{ profile_user.get_level() }}</strong></span>
                    <span>{{ profile_user.points }} XP</span>
                    {% if profile_user.is_banned %}
                    <span style="color:var(--ember); font-weight:700;">⛔ Banlı</span>
                    {% else %}
                    <span style="color:var(--green); font-weight:700;">✔ Aktiv</span>
                    {% endif %}
                    {% if profile_user.is_muted %}
                    <span style="color:var(--gold); font-weight:700;">🔇 Susdurulub</span>
                    {% endif %}
                </div>

                {% if profile_user.bio %}
                <p style="margin-top:0.75rem; font-size:0.875rem; color:var(--ink-2); line-height:1.7;">
                    {{ profile_user.bio }}
                </p>
                {% endif %}

                {% if profile_user.twitter_link or profile_user.instagram_link or profile_user.discord_link %}
                <div style="display:flex; gap:0.75rem; margin-top:0.75rem; flex-wrap:wrap;">
                    {% if profile_user.twitter_link %}
                    <a href="{{ profile_user.twitter_link }}" target="_blank" class="btn btn-ghost btn-sm">
                        🐦 Twitter
                    </a>
                    {% endif %}
                    {% if profile_user.instagram_link %}
                    <a href="{{ profile_user.instagram_link }}" target="_blank" class="btn btn-ghost btn-sm"
                       style="color:var(--ember); border-color:rgba(255,77,109,0.3);">
                        📷 Instagram
                    </a>
                    {% endif %}
                    {% if profile_user.discord_link %}
                    <a href="{{ profile_user.discord_link }}" target="_blank" class="btn btn-ghost btn-sm"
                       style="color:var(--violet); border-color:rgba(168,85,247,0.3);">
                        🎮 Discord
                    </a>
                    {% endif %}
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Admin moderation panel -->
    {% if current_user.is_authenticated and current_user.is_admin and profile_user.id != current_user.id %}
    <div class="card card-inner">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--ember);">
            🛡 Moderasiya
        </h2>

        <div style="margin-bottom:0.75rem;">
            <div style="font-size:0.78rem; color:var(--ink-3); font-family:var(--font-mono); margin-bottom:0.5rem;">
                Ban müddəti:
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
                {% for d, label in [(1,'1 gün'),(7,'7 gün'),(30,'30 gün'),(90,'3 ay'),(180,'6 ay'),(365,'12 ay')] %}
                <a href="/admin/ban-user/{{ profile_user.id }}?duration={{ d }}"
                   class="btn btn-ember btn-sm">{{ label }}</a>
                {% endfor %}
                <a href="/admin/ban-user/{{ profile_user.id }}?duration=forever"
                   class="btn btn-danger" style="font-weight:900;">Ömürlük</a>
                {% if profile_user.is_banned %}
                <a href="/admin/unban-user/{{ profile_user.id }}" class="btn btn-green btn-sm">Banı aç</a>
                {% endif %}
            </div>
        </div>

        <div>
            <div style="font-size:0.78rem; color:var(--ink-3); font-family:var(--font-mono); margin-bottom:0.5rem;">
                Susdurma müddəti:
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
                {% for d, label in [(1,'1 gün'),(7,'7 gün'),(30,'30 gün')] %}
                <a href="/admin/mute-user/{{ profile_user.id }}?duration={{ d }}"
                   class="btn btn-gold btn-sm">{{ label }}</a>
                {% endfor %}
                {% if profile_user.is_muted %}
                <a href="/admin/unmute-user/{{ profile_user.id }}" class="btn btn-green btn-sm">Susturmanı aç</a>
                {% endif %}
            </div>
        </div>
    </div>
    {% endif %}

</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  ADMIN_HTML
# ────────────────────────────────────────────────────────────
ADMIN_HTML = """
{% extends "base.html" %}
{% block title %}Admin Panel - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="padding-top:2.5rem; padding-bottom:4rem;">

    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:2rem; flex-wrap:wrap;">
        <h1 style="font-size:1.8rem; font-weight:900; color:var(--gold); font-family:var(--font-display);">
            ⚙ Admin Panel
        </h1>
        <a href="/admin/fetch-news" class="btn btn-green">
            🔄 Xəbərləri avtomatik çək
        </a>
    </div>

    <!-- Two-column: Add News + Add Manga -->
    <div class="grid-2" style="margin-bottom:2rem;">

        <!-- Add News -->
        <div class="card card-inner">
            <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
                + Yeni Xəbər
            </h2>
            <form action="/admin/add-news" method="POST" enctype="multipart/form-data"
                  style="display:flex; flex-direction:column; gap:0.75rem;">
                <div class="form-group">
                    <label class="form-label">Başlıq</label>
                    <input type="text" name="title" required class="form-input" placeholder="Xəbər başlığı">
                </div>
                <div class="form-group">
                    <label class="form-label">Məzmun</label>
                    <textarea name="content" required rows="5" class="form-textarea" placeholder="Xəbər mətni..."></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Kateqoriya</label>
                    <select name="category" class="form-select">
                        {% for c in ['Anime','Manga','Webtoon','Manhua','Oyun','Ümumi'] %}
                        <option value="{{ c }}">{{ c }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Şəkil URL</label>
                    <input type="text" name="image_url" class="form-input" placeholder="https://…">
                </div>
                <div class="form-group">
                    <label class="form-label">və ya Şəkil Yüklə</label>
                    <input type="file" name="image_file" accept="image/*" class="form-input" style="padding:0.4rem;">
                </div>

                <!-- Dynamic content blocks -->
                <div id="blocksContainer" style="display:flex; flex-direction:column; gap:0.75rem;"></div>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                    <button type="button" onclick="addTextBlock()"
                            class="btn btn-ghost btn-sm">+ Mətn Bloku</button>
                    <button type="button" onclick="addImageBlock()"
                            class="btn btn-ghost btn-sm" style="color:var(--violet); border-color:rgba(168,85,247,0.3);">
                        + Şəkil Bloku
                    </button>
                </div>
                <button type="submit" class="btn btn-primary">Əlavə et</button>
            </form>
        </div>

        <!-- Add Manga -->
        <div class="card card-inner">
            <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--violet);">
                + Yeni Manqa / Anime
            </h2>
            <form action="/admin/add-manga" method="POST" enctype="multipart/form-data"
                  style="display:flex; flex-direction:column; gap:0.75rem;">
                <div class="form-group">
                    <label class="form-label">Başlıq</label>
                    <input type="text" name="title" required class="form-input" placeholder="Başlıq">
                </div>
                <div class="form-group">
                    <label class="form-label">Açıqlama</label>
                    <textarea name="description" required rows="3" class="form-textarea"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Növ</label>
                    <select name="type" class="form-select">
                        {% for t in ['anime','manga','manhwa','manhua','webtoon'] %}
                        <option value="{{ t }}">{{ t | capitalize }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Üz Şəkli URL</label>
                    <input type="text" name="cover_url" class="form-input" placeholder="https://…">
                </div>
                <div class="form-group">
                    <label class="form-label">və ya Şəkil Yüklə</label>
                    <input type="file" name="cover_file" accept="image/*" class="form-input" style="padding:0.4rem;">
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.6rem;">
                    <div class="form-group">
                        <label class="form-label">Reytinq</label>
                        <input type="number" step="0.1" name="rating" value="8.0" class="form-input">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Bölüm</label>
                        <input type="number" name="chapters" value="100" class="form-input">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Status</label>
                        <input type="text" name="status" value="Davam edir" class="form-input">
                    </div>
                </div>
                <button type="submit" class="btn btn-violet">Əlavə et</button>
            </form>
        </div>
    </div>

    <!-- Listicle generator -->
    <div class="card card-inner mb-6">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--gold);">
            📋 Siyahı Məqaləsi Yarat (AI)
        </h2>
        <form action="/admin/generate-listicle" method="POST"
              style="display:flex; gap:0.75rem; align-items:flex-end; flex-wrap:wrap;">
            <div class="form-group" style="flex:1; min-width:200px;">
                <label class="form-label">Mövzu</label>
                <input type="text" name="topic" required class="form-input"
                       placeholder="məs. best 10 isekai anime 2026">
            </div>
            <button type="submit" class="btn btn-gold">Yarat</button>
        </form>
    </div>

    <!-- Reports -->
    {% if report_details %}
    <div class="card card-inner mb-6">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--ember);">
            🚩 Şikayətlər ({{ report_details | length }})
        </h2>
        <div style="display:flex; flex-direction:column; gap:0.75rem;">
            {% for item in report_details %}
            <div style="background:var(--surface-2); border:1px solid var(--border);
                        border-radius:var(--radius-sm); padding:1rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; flex-wrap:wrap;">
                    <div>
                        <div style="font-size:0.85rem; color:var(--ink-2);">
                            <strong style="color:var(--ember);">{{ item.report.reporter.username }}</strong>
                            tərəfindən şikayət —
                            <span class="chip chip-ember" style="font-size:0.68rem;">{{ item.report.target_type }}</span>
                            #{{ item.report.target_id }}
                        </div>
                        <div style="font-size:0.78rem; color:var(--ink-3); margin-top:0.25rem;">
                            Səbəb: {{ item.report.reason }}
                        </div>
                        <div style="font-size:0.75rem; color:var(--ink-muted); margin-top:0.4rem;
                                    font-family:var(--font-mono);">
                            {{ item.snippet }}
                        </div>
                        <a href="{{ item.link }}" target="_blank"
                           style="font-size:0.72rem; color:var(--pulse);">Məzmuna bax ↗</a>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:0.4rem; flex-shrink:0;">
                        <a href="/admin/handle-report/{{ item.report.id }}" class="btn btn-green btn-sm">Həll et</a>
                        <a href="/admin/delete-report/{{ item.report.id }}" class="btn btn-danger">Sil</a>
                        {% if item.report.target_type == 'post' %}
                        <a href="/admin/delete-post/{{ item.report.target_id }}" class="btn btn-danger">Şərhi sil</a>
                        {% elif item.report.target_type == 'room' %}
                        <a href="/admin/delete-room/{{ item.report.target_id }}" class="btn btn-danger">Otağı sil</a>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- News list -->
    <div class="card card-inner mb-6">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--pulse);">
            📰 Mövcud Xəbərlər
        </h2>
        <div>
            {% for news in all_news %}
            <div class="admin-list-item">
                <span class="admin-list-item-title">{{ news.title }}</span>
                <div style="display:flex; gap:0.5rem; flex-shrink:0;">
                    <a href="/admin/edit-news/{{ news.id }}" class="btn btn-ghost btn-sm">Redaktə</a>
                    <a href="/admin/delete-news/{{ news.id }}" class="btn btn-danger">Sil</a>
                </div>
            </div>
            {% else %}
            <p style="color:var(--ink-3); font-size:0.875rem;">Xəbər yoxdur.</p>
            {% endfor %}
        </div>
    </div>

    <!-- Manga list -->
    <div class="card card-inner">
        <h2 style="font-size:1rem; font-weight:700; margin-bottom:1rem; color:var(--violet);">
            📚 Mövcud Manqa / Anime
        </h2>
        <div>
            {% for m in all_manga %}
            <div class="admin-list-item">
                <span class="admin-list-item-title">{{ m.title }}
                    <span class="chip chip-violet" style="font-size:0.65rem;">{{ m.type }}</span>
                </span>
                <div style="display:flex; gap:0.5rem; flex-shrink:0;">
                    <a href="/admin/edit-manga/{{ m.id }}" class="btn btn-ghost btn-sm">Redaktə</a>
                    <a href="/admin/delete-manga/{{ m.id }}" class="btn btn-danger">Sil</a>
                </div>
            </div>
            {% else %}
            <p style="color:var(--ink-3); font-size:0.875rem;">Məlumat yoxdur.</p>
            {% endfor %}
        </div>
    </div>

</div>

<script>
function blockShell(label, innerHtml) {
    const div = document.createElement('div');
    div.style.cssText = 'background:var(--surface-2); border:1px solid var(--border); border-radius:8px; padding:0.9rem;';
    div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
            <span style="font-size:0.8rem; font-weight:700; color:var(--ink-3);">${label}</span>
            <button type="button" onclick="this.closest('[data-block]').remove()"
                    style="font-size:0.75rem; color:var(--ember); background:none; border:none; cursor:pointer;">Sil</button>
        </div>
        ${innerHtml}
    `;
    div.setAttribute('data-block', '1');
    return div;
}
function addTextBlock() {
    const inner = `
        <input type="hidden" name="block_type" value="text">
        <textarea name="block_text" rows="4" class="form-textarea" placeholder="Mətn daxil edin"></textarea>
        <select name="block_layout" class="form-select" style="margin-top:0.5rem;">
            <option value="stack">Alt-alta</option>
            <option value="side">Yan-yana</option>
        </select>`;
    document.getElementById('blocksContainer').appendChild(blockShell('Mətn Bloku', inner));
}
function addImageBlock() {
    const inner = `
        <input type="hidden" name="block_type" value="image">
        <input type="text" name="block_image_url" class="form-input" placeholder="Şəkil URL" style="margin-bottom:0.4rem;">
        <input type="file" name="block_image_file" accept="image/*" class="form-input" style="padding:0.35rem;">
        <select name="block_layout" class="form-select" style="margin-top:0.5rem;">
            <option value="stack">Alt-alta</option>
            <option value="side">Yan-yana</option>
        </select>`;
    document.getElementById('blocksContainer').appendChild(blockShell('Şəkil Bloku', inner));
}
</script>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  EDIT_NEWS_HTML
# ────────────────────────────────────────────────────────────
EDIT_NEWS_HTML = """
{% extends "base.html" %}
{% block title %}Xəbəri Redaktə Et - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:820px; padding-top:2.5rem; padding-bottom:4rem;">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:2rem; flex-wrap:wrap; gap:1rem;">
        <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink);">✏ Xəbəri Redaktə Et</h1>
        <a href="/admin" class="btn btn-ghost btn-sm">← Admin panelinə qayıt</a>
    </div>

    <form method="POST" enctype="multipart/form-data" class="card card-inner-lg"
          style="display:flex; flex-direction:column; gap:1rem;">
        <div class="form-group">
            <label class="form-label">Başlıq</label>
            <input type="text" name="title" value="{{ news.title }}" required class="form-input">
        </div>
        <div class="form-group">
            <label class="form-label">Məzmun</label>
            <textarea name="content" required rows="8" class="form-textarea">{{ news.content }}</textarea>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
            <div class="form-group">
                <label class="form-label">Kateqoriya</label>
                <select name="category" class="form-select">
                    {% for c in ['Anime','Manga','Webtoon','Manhua','Oyun','Ümumi'] %}
                    <option value="{{ c }}" {% if news.category == c %}selected{% endif %}>{{ c }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Şəkil URL</label>
                <input type="text" name="image_url" value="{{ news.image_url or '' }}" class="form-input">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Yeni şəkil yüklə</label>
            <input type="file" name="image_file" accept="image/*" class="form-input" style="padding:0.4rem;">
        </div>

        <div class="divider"></div>
        <h3 style="font-size:0.95rem; font-weight:700; color:var(--pulse);">Məzmun Blokları</h3>
        <div id="blocksContainer" style="display:flex; flex-direction:column; gap:0.75rem;"></div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
            <button type="button" onclick="addTextBlock()" class="btn btn-ghost btn-sm">+ Mətn Bloku</button>
            <button type="button" onclick="addImageBlock()" class="btn btn-ghost btn-sm"
                    style="color:var(--violet); border-color:rgba(168,85,247,0.3);">+ Şəkil Bloku</button>
        </div>

        <button type="submit" class="btn btn-primary btn-lg" style="margin-top:0.5rem;">
            ✔ Yadda saxla
        </button>
    </form>
</div>

<script>
function blockShell(label, innerHtml) {
    const div = document.createElement('div');
    div.style.cssText = 'background:var(--surface-2); border:1px solid var(--border); border-radius:8px; padding:0.9rem;';
    div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
            <span style="font-size:0.8rem; font-weight:700; color:var(--ink-3);">${label}</span>
            <button type="button" onclick="this.closest('[data-block]').remove()"
                    style="font-size:0.75rem; color:var(--ember); background:none; border:none; cursor:pointer;">Sil</button>
        </div>
        ${innerHtml}
    `;
    div.setAttribute('data-block', '1');
    return div;
}
function addTextBlock(text='', layout='stack') {
    const inner = `
        <input type="hidden" name="block_type" value="text">
        <textarea name="block_text" rows="4" class="form-textarea">${text}</textarea>
        <select name="block_layout" class="form-select" style="margin-top:0.5rem;">
            <option value="stack" ${layout==='stack'?'selected':''}>Alt-alta</option>
            <option value="side"  ${layout==='side' ?'selected':''}>Yan-yana</option>
        </select>`;
    document.getElementById('blocksContainer').appendChild(blockShell('Mətn Bloku', inner));
}
function addImageBlock(url='', layout='stack') {
    const inner = `
        <input type="hidden" name="block_type" value="image">
        <input type="text" name="block_image_url" class="form-input" value="${url}" placeholder="Şəkil URL" style="margin-bottom:0.4rem;">
        <input type="file" name="block_image_file" accept="image/*" class="form-input" style="padding:0.35rem;">
        <select name="block_layout" class="form-select" style="margin-top:0.5rem;">
            <option value="stack" ${layout==='stack'?'selected':''}>Alt-alta</option>
            <option value="side"  ${layout==='side' ?'selected':''}>Yan-yana</option>
        </select>`;
    document.getElementById('blocksContainer').appendChild(blockShell('Şəkil Bloku', inner));
}
// Pre-fill existing blocks
window.addEventListener('DOMContentLoaded', () => {
    {% for block in news.blocks %}
        {% if block.block_type == 'text' %}
        addTextBlock({{ block.text_content | tojson }}, '{{ block.layout }}');
        {% else %}
        addImageBlock('{{ block.image_url or '' }}', '{{ block.layout }}');
        {% endif %}
    {% endfor %}
});
</script>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  EDIT_MANGA_HTML
# ────────────────────────────────────────────────────────────
EDIT_MANGA_HTML = """
{% extends "base.html" %}
{% block title %}Manqanı Redaktə Et - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:720px; padding-top:2.5rem; padding-bottom:4rem;">
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:2rem; flex-wrap:wrap; gap:1rem;">
        <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink);">✏ Manqanı Redaktə Et</h1>
        <a href="/admin" class="btn btn-ghost btn-sm">← Admin panelinə qayıt</a>
    </div>

    <form method="POST" enctype="multipart/form-data" class="card card-inner-lg"
          style="display:flex; flex-direction:column; gap:1rem;">
        <div class="form-group">
            <label class="form-label">Başlıq</label>
            <input type="text" name="title" value="{{ manga.title }}" required class="form-input">
        </div>
        <div class="form-group">
            <label class="form-label">Açıqlama</label>
            <textarea name="description" required rows="5" class="form-textarea">{{ manga.description }}</textarea>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
            <div class="form-group">
                <label class="form-label">Növ</label>
                <select name="type" class="form-select">
                    {% for t in ['anime','manga','manhwa','manhua','webtoon'] %}
                    <option value="{{ t }}" {% if manga.type == t %}selected{% endif %}>{{ t | capitalize }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Status</label>
                <input type="text" name="status" value="{{ manga.status }}" class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Reytinq</label>
                <input type="number" step="0.1" name="rating" value="{{ manga.rating }}" class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Bölüm sayı</label>
                <input type="number" name="chapters" value="{{ manga.chapters }}" class="form-input">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Üz Şəkli URL</label>
            <input type="text" name="cover_url" value="{{ manga.cover_url or '' }}" class="form-input">
        </div>
        <div class="form-group">
            <label class="form-label">Yeni üz şəkli yüklə</label>
            <input type="file" name="cover_file" accept="image/*" class="form-input" style="padding:0.4rem;">
        </div>
        <button type="submit" class="btn btn-primary btn-lg" style="margin-top:0.5rem;">
            ✔ Yadda saxla
        </button>
    </form>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  ABOUT_HTML
# ────────────────────────────────────────────────────────────
ABOUT_HTML = """
{% extends "base.html" %}
{% block title %}Haqqımızda - Mi Digital Verse{% endblock %}
{% block content %}

<div class="page-hero">
    <div class="container" style="text-align:center;">
        <h1>🌐 <span>Haqqımızda</span></h1>
    </div>
</div>

<div class="container" style="max-width:780px; padding-top:3rem; padding-bottom:4rem;">
    <div class="card card-inner-lg" style="
        background: linear-gradient(135deg, var(--surface-2), var(--surface));
        border-color: var(--border-hover);
        position:relative; overflow:hidden;
    ">
        <div style="position:absolute; top:-60px; right:-60px; width:260px; height:260px;
                    border-radius:50%; background:radial-gradient(circle, var(--violet-dim) 0%, transparent 70%);
                    pointer-events:none;"></div>

        <div style="position:relative;">
            <div class="chip chip-pulse" style="margin-bottom:1.5rem;">Bizim haqqımızda</div>

            <p style="font-size:1.05rem; line-height:1.9; color:var(--ink-2); margin-bottom:1.25rem;">
                <strong style="color:var(--pulse);">Mi Digital Verse</strong>, anime, manhwa, manhua və manga
                həvəskarları üçün yaradılmış müasir rəqəmsal məkandır. Məqsədimiz pərəstişkarlara ən son
                xəbərləri, keyfiyyətli analizləri və interaktiv icma təcrübəsini bir araya gətirməkdir.
            </p>
            <p style="font-size:1.05rem; line-height:1.9; color:var(--ink-2); margin-bottom:1.25rem;">
                Biz inanırıq ki, hər bir pərəstişkarın səsi burada eşidilməlidir. Ona görə də saytımızda
                müzakirə otaqları, nailiyyətlər və ünvan sistemi qurmuşuq. Gələcəkdə daha çox funksiya
                və məzmun əlavə edərək böyüməyə davam edəcəyik.
            </p>
            <p style="font-size:1.05rem; line-height:1.9; color:var(--ink-2);">
                Mi Digital Verse ailəsinə qoşulun və rəqəmsal dünyada öz yerinizi alın!
            </p>

            <div class="divider"></div>

            <div class="grid-3">
                {% for icon, label, desc in [
                    ('🎌','Anime','Geniş anime kataloqu'),
                    ('📖','Manga','Manga, manhwa, manhua'),
                    ('💬','İcma','Aktiv müzakirə otaqları')
                ] %}
                <div style="text-align:center; padding:1rem 0.5rem;">
                    <div style="font-size:2rem; margin-bottom:0.5rem;">{{ icon }}</div>
                    <div style="font-weight:700; color:var(--ink); margin-bottom:0.25rem;">{{ label }}</div>
                    <div style="font-size:0.78rem; color:var(--ink-3);">{{ desc }}</div>
                </div>
                {% endfor %}
            </div>

            <div style="text-align:center; margin-top:2rem;">
                <a href="/register" class="btn btn-primary btn-lg">Qoşulun →</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  SEARCH_HTML
# ────────────────────────────────────────────────────────────
SEARCH_HTML = """
{% extends "base.html" %}
{% block title %}Axtarış: {{ q }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="padding-top:2.5rem; padding-bottom:4rem;">
    <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink); margin-bottom:0.4rem;">
        🔍 Axtarış nəticəsi
    </h1>
    <p style="color:var(--ink-3); margin-bottom:2rem; font-family:var(--font-mono); font-size:0.85rem;">
        «{{ q }}» üçün nəticələr
    </p>

    <!-- Re-search bar -->
    <form action="/search" method="GET"
          style="display:flex; gap:0.75rem; margin-bottom:2.5rem; max-width:600px;">
        <input type="text" name="q" value="{{ q }}" class="form-input" style="flex:1;"
               placeholder="Yenidən axtar...">
        <button type="submit" class="btn btn-primary">Axtar</button>
    </form>

    <!-- News results -->
    <div class="section-heading">
        <span class="section-heading-dot"></span>
        <h2>Xəbərlər</h2>
        <div class="section-heading-line"></div>
        <span style="font-family:var(--font-mono); font-size:0.78rem; color:var(--ink-3);">
            {{ news_results | length }} nəticə
        </span>
    </div>
    <div class="grid-2" style="margin-bottom:2.5rem;">
        {% for n in news_results %}
        <a href="/news/{{ n.id }}" class="news-card">
            <div class="news-card-body">
                <div class="news-card-category">{{ n.category }}</div>
                <div class="news-card-title">{{ n.title }}</div>
                <div class="news-card-meta">
                    <span>📅 {{ n.published_at.strftime('%d.%m.%Y') }}</span>
                </div>
            </div>
        </a>
        {% else %}
        <div class="card card-inner" style="grid-column:1/-1; color:var(--ink-3); text-align:center; padding:2rem;">
            Xəbər tapılmadı.
        </div>
        {% endfor %}
    </div>

    <!-- Manga results -->
    <div class="section-heading">
        <span class="section-heading-dot" style="background:var(--violet); box-shadow:0 0 8px var(--violet);"></span>
        <h2>Manqa / Anime</h2>
        <div class="section-heading-line"></div>
        <span style="font-family:var(--font-mono); font-size:0.78rem; color:var(--ink-3);">
            {{ manga_results | length }} nəticə
        </span>
    </div>
    <div class="grid-4">
        {% for m in manga_results %}
        <a href="/manga/{{ m.id }}" class="manga-card">
            <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="manga-card-img">
            <div class="manga-card-body">
                <div class="manga-card-title">{{ m.title }}</div>
                <div class="manga-card-sub">{{ m.type | capitalize }}</div>
                <div class="manga-card-rating">⭐ {{ m.rating }}</div>
            </div>
        </a>
        {% else %}
        <div class="card card-inner" style="grid-column:1/-1; color:var(--ink-3); text-align:center; padding:2rem;">
            Manqa / Anime tapılmadı.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  NOTIFICATIONS_HTML
# ────────────────────────────────────────────────────────────
NOTIFICATIONS_HTML = """
{% extends "base.html" %}
{% block title %}Bildirişlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:720px; padding-top:2.5rem; padding-bottom:4rem;">
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:2rem; flex-wrap:wrap; gap:1rem;">
        <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink);">🔔 Bildirişlər</h1>
        <a href="/notifications/mark-all-read" class="btn btn-ghost btn-sm">
            ✔ Hamısını oxunmuş et
        </a>
    </div>

    <div class="space-y">
        {% for n in notifications %}
        <div class="notif-item {% if not n.is_read %}unread{% endif %}">
            <div style="flex:1; min-width:0;">
                <div class="notif-item-msg">{{ n.message }}</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:0.4rem; flex-shrink:0;">
                <div class="notif-item-time">{{ n.created_at.strftime('%d.%m.%Y %H:%M') }}</div>
                {% if not n.is_read %}
                <a href="/notifications/mark-read/{{ n.id }}"
                   style="font-size:0.72rem; color:var(--pulse); white-space:nowrap;">
                    Oxunmuş
                </a>
                {% else %}
                <span class="chip chip-green" style="font-size:0.62rem;">✔</span>
                {% endif %}
            </div>
        </div>
        {% else %}
        <div class="card card-inner" style="text-align:center; color:var(--ink-3); padding:3rem;">
            Bildiriş yoxdur.
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  QUESTS_HTML
# ────────────────────────────────────────────────────────────
QUESTS_HTML = """
{% extends "base.html" %}
{% block title %}Görəvlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:720px; padding-top:2.5rem; padding-bottom:4rem;">
    <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink); margin-bottom:2rem;">📋 Görəvlər</h1>

    <div class="section-heading">
        <span class="section-heading-dot"></span>
        <h2>Gündəlik</h2>
        <div class="section-heading-line"></div>
    </div>
    <div class="space-y mb-6">
        {% for quest in daily_quests %}
        {% set progress = user_quests.get(quest.id) %}
        <div class="quest-item {% if progress and progress.completed %}completed{% endif %}">
            <div class="quest-item-header">
                <span class="quest-item-name">{{ quest.name }}</span>
                <span class="quest-item-xp">+{{ quest.reward_xp }} XP</span>
            </div>
            <div class="quest-item-desc">{{ quest.description }}</div>
            {% if progress and progress.completed %}
            <div class="quest-complete-badge">✔ Tamamlandı</div>
            {% else %}
            <div class="xp-bar-track" style="height:4px;">
                <div class="xp-bar-fill"
                     style="width:{{ ((progress.progress / quest.target_value) * 100) if progress else 0 }}%;"></div>
            </div>
            <div style="font-size:0.7rem; color:var(--ink-3); font-family:var(--font-mono); margin-top:0.3rem;">
                {{ progress.progress if progress else 0 }} / {{ quest.target_value }}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="section-heading">
        <span class="section-heading-dot" style="background:var(--gold); box-shadow:0 0 8px var(--gold);"></span>
        <h2>Həftəlik</h2>
        <div class="section-heading-line"></div>
    </div>
    <div class="space-y">
        {% for quest in weekly_quests %}
        {% set progress = user_quests.get(quest.id) %}
        <div class="quest-item {% if progress and progress.completed %}completed{% endif %}">
            <div class="quest-item-header">
                <span class="quest-item-name">{{ quest.name }}</span>
                <span class="quest-item-xp">+{{ quest.reward_xp }} XP</span>
            </div>
            <div class="quest-item-desc">{{ quest.description }}</div>
            {% if progress and progress.completed %}
            <div class="quest-complete-badge">✔ Tamamlandı</div>
            {% else %}
            <div class="xp-bar-track" style="height:4px;">
                <div class="xp-bar-fill"
                     style="width:{{ ((progress.progress / quest.target_value) * 100) if progress else 0 }}%;"></div>
            </div>
            <div style="font-size:0.7rem; color:var(--ink-3); font-family:var(--font-mono); margin-top:0.3rem;">
                {{ progress.progress if progress else 0 }} / {{ quest.target_value }}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ────────────────────────────────────────────────────────────
#  ACHIEVEMENTS_HTML
# ────────────────────────────────────────────────────────────
ACHIEVEMENTS_HTML = """
{% extends "base.html" %}
{% block title %}Nailiyyətlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="container" style="max-width:820px; padding-top:2.5rem; padding-bottom:4rem;">
    <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink); margin-bottom:2rem;">🏆 Nailiyyətlər</h1>

    <div class="grid-2">
        {% for ach in all_achievements %}
        <div style="
            background: var(--surface);
            border: 1px solid {% if earned_achievements[ach.id] %}rgba(34,211,165,0.4){% else %}var(--border){% endif %};
            border-radius: var(--radius-md);
            padding: 1.25rem;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            opacity: {% if ach.hidden and not earned_achievements[ach.id] %}0.42{% else %}1{% endif %};
            transition: var(--transition);
        ">
            <div style="font-size:2rem; line-height:1; flex-shrink:0;">{{ ach.badge_icon }}</div>
            <div>
                <div style="font-weight:700; color:var(--ink); margin-bottom:0.2rem;">{{ ach.name }}</div>
                <div style="font-size:0.8rem; color:var(--ink-3); margin-bottom:0.4rem;">{{ ach.description }}</div>
                {% if earned_achievements[ach.id] %}
                <span class="chip chip-green" style="font-size:0.7rem;">✔ Qazanılıb</span>
                {% elif ach.hidden %}
                <span class="chip chip-violet" style="font-size:0.7rem;">🔒 Gizli</span>
                {% else %}
                <span style="font-size:0.72rem; color:var(--ink-muted);">Hələ qazanılmayıb</span>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ════════════════════════════════════════════════════════════
#  TEMPLATE REGISTRY
# ════════════════════════════════════════════════════════════
templates = {
    'base.html':         BASE_HTML,
    'index.html':        INDEX_HTML,
    'news_list.html':    NEWS_LIST_HTML,
    'news_detail.html':  NEWS_DETAIL_HTML,
    'manga_list.html':   MANGA_LIST_HTML,
    'manga_detail.html': MANGA_DETAIL_HTML,
    'community.html':    COMMUNITY_HTML,
    'room.html':         ROOM_HTML,
    'profile.html':      PROFILE_HTML,
    'user_profile.html': USER_PROFILE_HTML,
    'admin.html':        ADMIN_HTML,
    'edit_news.html':    EDIT_NEWS_HTML,
    'edit_manga.html':   EDIT_MANGA_HTML,
    'search.html':       SEARCH_HTML,
    'notifications.html':NOTIFICATIONS_HTML,
    'quests.html':       QUESTS_HTML,
    'achievements.html': ACHIEVEMENTS_HTML,
    'about.html':        ABOUT_HTML,
}

app.jinja_loader = DictLoader(templates)

# ════════════════════════════════════════════════════════════
#  CONTEXT PROCESSORS
# ════════════════════════════════════════════════════════════
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def inject_unread_notifications():
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {'unread_notifications_count': unread}
    return {'unread_notifications_count': 0}

# ════════════════════════════════════════════════════════════
#  ROUTES — PUBLIC
# ════════════════════════════════════════════════════════════
@app.route('/')
def index():
    latest_news = News.query.order_by(News.published_at.desc()).limit(5).all()
    most_read   = News.query.order_by(News.views.desc()).limit(5).all()
    featured    = Manga.query.order_by(Manga.rating.desc()).limit(4).all()
    return render_template('index.html', latest_news=latest_news,
                           most_read=most_read, featured=featured)

@app.route('/news')
def news_list():
    all_news = News.query.order_by(News.published_at.desc()).all()
    return render_template('news_list.html', all_news=all_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news = News.query.get_or_404(news_id)
    if can_increment_view(news.id):
        news.views += 1
        db.session.commit()
        if current_user.is_authenticated:
            current_user.news_read_count += 1
            add_xp(current_user, 2)
            update_quest_progress(current_user, 'news_read', 1)
            check_achievements(current_user)
    return render_template('news_detail.html', news=news)

@app.route('/category/<string:cat>')
def category(cat):
    all_news = News.query.filter(News.category.ilike(f'%{cat}%')).order_by(News.published_at.desc()).all()
    return render_template('news_list.html', all_news=all_news)

@app.route('/manga')
def manga_list():
    type_filter = request.args.get('type', '')
    q           = request.args.get('q', '')
    if q:
        mangas = Manga.query.filter(Manga.title.contains(q) | Manga.description.contains(q)).all()
    elif type_filter:
        mangas = Manga.query.filter_by(type=type_filter).all()
    else:
        mangas = Manga.query.all()
    return render_template('manga_list.html', mangas=mangas)

@app.route('/manga/<int:manga_id>')
def manga_detail(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    if can_increment_view(manga.id):
        manga.views += 1
        db.session.commit()
    return render_template('manga_detail.html', manga=manga)

@app.route('/like-manga/<int:manga_id>', methods=['POST'])
@login_required
def like_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    manga.likes += 1
    db.session.commit()
    current_user.likes_count += 1
    add_xp(current_user, 1)
    update_quest_progress(current_user, 'like', 1)
    check_achievements(current_user)
    add_notification(current_user, f"Siz {manga.title} əsərini bəyəndiniz.")
    return redirect(url_for('manga_detail', manga_id=manga.id))

@app.route('/search')
def search():
    q           = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '')
    news_results  = []
    manga_results = []
    if q:
        news_results  = News.query.filter(News.title.contains(q) | News.content.contains(q)).all()
        manga_results = Manga.query.filter(Manga.title.contains(q) | Manga.description.contains(q)).all()
        if type_filter:
            manga_results = [m for m in manga_results if m.type == type_filter]
    return render_template('search.html', q=q, news_results=news_results, manga_results=manga_results)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/community')
def community():
    rooms    = Room.query.order_by(Room.created_at.desc()).all()
    all_news = News.query.all()
    return render_template('community.html', rooms=rooms, all_news=all_news)

@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'GET':
        all_news         = News.query.all()
        selected_news_id = request.args.get('news_id')
        return render_template_string('''
        {% extends "base.html" %}
        {% block content %}
        <div class="container" style="max-width:640px; padding-top:2.5rem; padding-bottom:4rem;">
            <h1 style="font-size:1.6rem; font-weight:900; color:var(--ink); margin-bottom:2rem;">
                💬 Yeni Müzakirə Otağı
            </h1>
            <form method="POST" class="card card-inner-lg" style="display:flex; flex-direction:column; gap:1rem;">
                <div class="form-group">
                    <label class="form-label">Otaq adı</label>
                    <input type="text" name="room_name" placeholder="Otaq adını daxil edin..."
                           required class="form-input">
                </div>
                <div class="form-group">
                    <label class="form-label">Xəbər seç (istəyə bağlı)</label>
                    <select name="news_id" class="form-select">
                        <option value="">—</option>
                        {% for n in all_news %}
                        <option value="{{ n.id }}"
                            {% if selected_news_id and n.id == selected_news_id|int %}selected{% endif %}>
                            {{ n.title[:60] }}{% if n.title|length > 60 %}…{% endif %}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <button type="submit" class="btn btn-primary btn-lg" style="justify-content:center;">
                    Otağı yarat
                </button>
            </form>
        </div>
        {% endblock %}
        ''', all_news=all_news,
             selected_news_id=int(selected_news_id) if selected_news_id else None)
    else:
        name    = request.form.get('room_name', '').strip()
        news_id = request.form.get('news_id', '')
        if not name:
            flash('Otaq adı boş ola bilməz')
            return redirect(url_for('community'))
        room = Room(name=name, news_id=int(news_id) if news_id else None,
                    creator_id=current_user.id)
        db.session.add(room)
        db.session.commit()
        update_quest_progress(current_user, 'room_create', 1)
        check_achievements(current_user)
        if room.news_id:
            news = News.query.get(room.news_id)
            if news and news.author_id and news.author_id != current_user.id:
                author = User.query.get(news.author_id)
                if author:
                    add_notification(author,
                        f"{current_user.username} '{news.title}' xəbəri üçün müzakirə otağı yaratdı.")
        return redirect(url_for('community'))

@app.route('/room/<int:room_id>')
def room(room_id):
    room  = Room.query.get_or_404(room_id)
    posts = Post.query.filter_by(room_id=room_id).order_by(Post.created_at.asc()).all()
    return render_template('room.html', room=room, posts=posts)

@app.route('/post/<int:room_id>', methods=['POST'])
@login_required
def add_post(room_id):
    content    = request.form.get('content', '').strip()
    is_spoiler = request.form.get('is_spoiler') == '1'
    if not content:
        return redirect(url_for('room', room_id=room_id))
    post = Post(room_id=room_id, user_id=current_user.id,
                content=content, is_spoiler=is_spoiler)
    db.session.add(post)
    db.session.commit()
    add_xp(current_user, 5)
    update_quest_progress(current_user, 'post', 1)
    check_achievements(current_user)
    r = Room.query.get(room_id)
    if r and r.creator_id != current_user.id:
        owner = User.query.get(r.creator_id)
        if owner:
            add_notification(owner,
                f"{current_user.username} '{r.name}' otağında yeni mesaj yazdı.")
    return redirect(url_for('room', room_id=room_id))

@app.route('/report/submit', methods=['POST'])
@login_required
def report_submit():
    target_type = request.form.get('target_type')
    target_id   = int(request.form.get('target_id'))
    reason      = request.form.get('reason', '')
    if target_type not in ['post', 'room']:
        flash('Səhv şikayət növü.')
        return redirect(request.referrer or url_for('index'))
    report = Report(reporter_id=current_user.id, target_type=target_type,
                    target_id=target_id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/report/post/<int:post_id>', methods=['POST'])
@login_required
def report_post(post_id):
    post   = Post.query.get_or_404(post_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='post',
                    target_id=post.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/report/room/<int:room_id>', methods=['POST'])
@login_required
def report_room(room_id):
    r      = Room.query.get_or_404(room_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='room',
                    target_id=r.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/like-news/<int:news_id>', methods=['POST'])
@login_required
def like_news(news_id):
    news          = News.query.get_or_404(news_id)
    existing_like = NewsLike.query.filter_by(user_id=current_user.id, news_id=news.id).first()
    if existing_like:
        db.session.delete(existing_like)
        news.likes = max(0, news.likes - 1)
        db.session.commit()
        flash('Bəyənmə geri alındı.')
    else:
        like = NewsLike(user_id=current_user.id, news_id=news.id)
        db.session.add(like)
        news.likes += 1
        db.session.commit()
        add_xp(current_user, 1)
        update_quest_progress(current_user, 'like', 1)
        check_achievements(current_user)
        if news.author_id and news.author_id != current_user.id:
            author = User.query.get(news.author_id)
            if author:
                add_notification(author,
                    f"{current_user.username} sizin '{news.title}' xəbərinizi bəyəndi.")
    return redirect(url_for('news_detail', news_id=news.id))

# ════════════════════════════════════════════════════════════
#  ROUTES — AUTH
# ════════════════════════════════════════════════════════════
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not email or not password:
            flash('Bütün sahələr doldurulmalıdır')
            return redirect(url_for('index'))
        if not is_strong_password(password):
            flash('Şifrə ən az 8 simvol, hərf və rəqəm olmalıdır')
            return redirect(url_for('index'))
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('Email formatı düzgün deyil')
            return redirect(url_for('index'))
        if User.query.filter_by(username=username).first():
            flash('Bu istifadəçi adı artıq mövcuddur')
            return redirect(url_for('index'))
        if User.query.filter_by(email=email).first():
            flash('Bu email artıq qeydiyyatdan keçib')
            return redirect(url_for('index'))
        user = User(username=username, email=email,
                    password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        start_title = Title.query.filter_by(name="Başlanğıc").first()
        if start_title:
            user.title_id = start_title.id
            ut = UserTitle(user_id=user.id, title_id=start_title.id)
            db.session.add(ut)
            db.session.commit()
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    user     = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        if user.is_banned:
            if user.banned_until and user.banned_until < datetime.now():
                user.is_banned    = False
                user.banned_until = None
                user.banned_reason= ''
                db.session.commit()
            else:
                flash('Hesabınız banlandı.')
                return redirect(url_for('index'))
        login_user(user)
        daily_reward(user)
        return redirect(url_for('index'))
    flash('İstifadəçi adı və ya şifrə yanlışdır')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ════════════════════════════════════════════════════════════
#  ROUTES — PROFILE
# ════════════════════════════════════════════════════════════
@app.route('/profile')
@login_required
def profile():
    claimed_today  = (current_user.last_login_date == date.today().isoformat())
    reset_user_quests(current_user)
    daily_quests   = Quest.query.filter_by(is_daily=True).all()
    weekly_quests  = Quest.query.filter_by(is_weekly=True).all()
    user_quests    = {uq.quest_id: uq for uq in current_user.quests}
    all_achievements  = Achievement.query.all()
    earned_ids        = [ua.achievement_id for ua in current_user.achievements]
    earned_achievements = {ach.id: (ach.id in earned_ids) for ach in all_achievements}
    earned_titles = get_earned_titles(current_user)
    return render_template('profile.html',
                           claimed_today=claimed_today,
                           daily_quests=daily_quests,
                           weekly_quests=weekly_quests,
                           user_quests=user_quests,
                           all_achievements=all_achievements,
                           earned_achievements=earned_achievements,
                           earned_titles=earned_titles)

@app.route('/profile/update-bio', methods=['POST'])
@login_required
def update_bio():
    current_user.bio            = request.form.get('bio', '').strip()
    current_user.twitter_link   = request.form.get('twitter_link', '').strip()
    current_user.instagram_link = request.form.get('instagram_link', '').strip()
    current_user.discord_link   = request.form.get('discord_link', '').strip()
    db.session.commit()
    flash('Profil yeniləndi')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password     = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Hazırkı şifrə yanlışdır')
    elif new_password != confirm_password:
        flash('Yeni şifrələr uyğun gəlmir')
    elif not is_strong_password(new_password):
        flash('Şifrə ən az 8 simvol, hərf və rəqəm olmalıdır')
    else:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Şifrə yeniləndi')
    return redirect(url_for('profile'))

@app.route('/profile/set-active-title/<int:title_id>', methods=['POST'])
@login_required
def set_active_title(title_id):
    title = Title.query.get_or_404(title_id)
    if UserTitle.query.filter_by(user_id=current_user.id, title_id=title.id).first():
        current_user.title_id = title.id
        db.session.commit()
        flash(f"Aktiv ünvan: {title.name}")
    else:
        flash("Bu ünvana sahib deyilsiniz.")
    return redirect(url_for('profile'))

@app.route('/profile/set-showcase', methods=['POST'])
@login_required
def set_showcase():
    s1 = request.form.get('showcase1', '')
    s2 = request.form.get('showcase2', '')
    s3 = request.form.get('showcase3', '')
    current_user.showcase1_id = int(s1) if s1 else None
    current_user.showcase2_id = int(s2) if s2 else None
    current_user.showcase3_id = int(s3) if s3 else None
    db.session.commit()
    flash("Vitrin yeniləndi")
    return redirect(url_for('profile'))

@app.route('/claim-daily', methods=['POST'])
@login_required
def claim_daily():
    if daily_reward(current_user):
        flash('Günlük ödül alındı!')
    else:
        flash('Bu gün artıq ödül almısınız.')
    return redirect(url_for('profile'))

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Fayl seçilməyib')
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file.filename == '':
        flash('Fayl seçilməyib')
        return redirect(url_for('profile'))
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            flash('Yalnız şəkil faylları yükləyə bilərsiniz')
            return redirect(url_for('profile'))
        filename = f"{current_user.id}_{datetime.utcnow().timestamp()}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        current_user.avatar = filename
        db.session.commit()
        flash('Profil şəkli yeniləndi')
    return redirect(url_for('profile'))

@app.route('/user/<string:username>')
def user_profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_profile.html', profile_user=profile_user)

# ════════════════════════════════════════════════════════════
#  ROUTES — NOTIFICATIONS
# ════════════════════════════════════════════════════════════
@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/mark-read/<int:notif_id>')
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    flash("Bütün bildirişlər oxunmuş işarələndi")
    return redirect(url_for('notifications'))

# ════════════════════════════════════════════════════════════
#  ROUTES — QUESTS & ACHIEVEMENTS (standalone pages)
# ════════════════════════════════════════════════════════════
@app.route('/quests')
@login_required
def quests_page():
    reset_user_quests(current_user)
    daily_quests  = Quest.query.filter_by(is_daily=True).all()
    weekly_quests = Quest.query.filter_by(is_weekly=True).all()
    user_quests   = {uq.quest_id: uq for uq in current_user.quests}
    return render_template('quests.html',
                           daily_quests=daily_quests,
                           weekly_quests=weekly_quests,
                           user_quests=user_quests)

@app.route('/achievements')
@login_required
def achievements_page():
    all_achievements = Achievement.query.all()
    earned_ids       = [ua.achievement_id for ua in current_user.achievements]
    earned_achievements = {ach.id: (ach.id in earned_ids) for ach in all_achievements}
    return render_template('achievements.html',
                           all_achievements=all_achievements,
                           earned_achievements=earned_achievements)

# ════════════════════════════════════════════════════════════
#  ROUTES — ADMIN
# ════════════════════════════════════════════════════════════
@app.route('/admin')
@login_required
@admin_required
def admin():
    all_news  = News.query.all()
    all_manga = Manga.query.all()
    all_users = User.query.all()
    reports   = Report.query.filter_by(handled=False).all()
    report_details = []
    for report in reports:
        if report.target_type == 'post':
            target          = Post.query.get(report.target_id)
            content_snippet = target.content[:100] if target else 'Silinmiş'
            link            = url_for('room', room_id=target.room_id) if target else '#'
        elif report.target_type == 'room':
            target          = Room.query.get(report.target_id)
            content_snippet = target.name if target else 'Silinmiş'
            link            = url_for('room', room_id=report.target_id) if target else '#'
        else:
            content_snippet = ''
            link            = '#'
        report_details.append({'report': report, 'snippet': content_snippet, 'link': link})
    return render_template('admin.html', all_news=all_news, all_manga=all_manga,
                           all_users=all_users, report_details=report_details)

@app.route('/admin/fetch-news')
@login_required
@admin_required
def fetch_news():
    articles = fetch_and_generate_news()
    count    = 0
    for art in articles:
        title             = art.get('title', 'Xəbər')
        content           = art.get('content', '')
        category          = art.get('category', 'Ümumi')
        image_keywords    = art.get('image_search_keywords', title)
        image_url         = art.get('image_url', '')
        if not image_url:
            image_url = get_image_url(image_keywords)
        if title and content:
            news = News(title=title, content=content, category=category,
                        image_url=image_url, author_id=current_user.id)
            db.session.add(news)
            count += 1
    db.session.commit()
    flash(f"{count} xəbər uğurla əlavə edildi.")
    return redirect(url_for('admin'))

@app.route('/admin/generate-listicle', methods=['POST'])
@login_required
@admin_required
def admin_generate_listicle():
    topic = request.form.get('topic', '').strip()
    if not topic:
        flash('Mövzu daxil edin')
        return redirect(url_for('admin'))
    article = generate_listicle(topic)
    if article:
        title             = article.get('title', topic)
        content           = article.get('content', '')
        category          = article.get('category', 'Ümumi')
        image_keywords    = article.get('image_search_keywords', title)
        image_url         = get_image_url(image_keywords)
        news = News(title=title, content=content, category=category,
                    image_url=image_url, author_id=current_user.id)
        db.session.add(news)
        db.session.commit()
        flash('Siyahı məqaləsi yaradıldı.')
    else:
        flash('Məqalə yaradıla bilmədi.')
    return redirect(url_for('admin'))

@app.route('/admin/add-news', methods=['POST'])
@login_required
@admin_required
def add_news():
    title      = request.form.get('title', '').strip()
    content    = request.form.get('content', '').strip()
    category   = request.form.get('category', 'Ümumi').strip()
    image_url  = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    if image_file and image_file.filename != '':
        filename = process_image(image_file, 800, 500)
        if filename:
            image_url = filename
    if title and content:
        if not image_url:
            image_url = get_image_url(title)
        news = News(title=title, content=content, category=category,
                    image_url=image_url, author_id=current_user.id)
        db.session.add(news)
        db.session.commit()
        # Content blocks
        block_types       = request.form.getlist('block_type')
        block_texts       = request.form.getlist('block_text')
        block_image_urls  = request.form.getlist('block_image_url')
        block_image_files = request.files.getlist('block_image_file')
        block_layouts     = request.form.getlist('block_layout')
        for i in range(len(block_types)):
            btype          = block_types[i]
            text_content   = block_texts[i] if i < len(block_texts) else ''
            image_url_block= block_image_urls[i] if i < len(block_image_urls) else ''
            layout         = block_layouts[i] if i < len(block_layouts) else 'stack'
            if btype == 'image' and i < len(block_image_files):
                f = block_image_files[i]
                if f and f.filename != '':
                    fname = process_image(f, 800, 500)
                    if fname:
                        image_url_block = fname
            if btype in ['text', 'image']:
                block = NewsBlock(news_id=news.id, block_type=btype,
                                  text_content=text_content,
                                  image_url=image_url_block,
                                  layout=layout, order=i)
                db.session.add(block)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/ban-user/<int:user_id>')
@login_required
@admin_required
def ban_user(user_id):
    user     = User.query.get_or_404(user_id)
    duration = request.args.get('duration', '1')
    if duration == 'forever':
        user.banned_until = None
        user.is_banned    = True
    else:
        user.banned_until = datetime.now() + timedelta(days=int(duration))
        user.is_banned    = True
    user.banned_reason = 'Admin tərəfindən banlandı'
    db.session.commit()
    flash(f"{user.username} banlandı.")
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin/mute-user/<int:user_id>')
@login_required
@admin_required
def mute_user(user_id):
    user     = User.query.get_or_404(user_id)
    duration = request.args.get('duration', '1')
    if duration == 'forever':
        user.muted_until = None
        user.is_muted    = True
    else:
        user.muted_until = datetime.now() + timedelta(days=int(duration))
        user.is_muted    = True
    user.muted_reason = 'Admin tərəfindən susturuldu'
    db.session.commit()
    flash(f"{user.username} susturuldu.")
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin/unban-user/<int:user_id>')
@login_required
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned    = False
    user.banned_until = None
    user.banned_reason= ''
    db.session.commit()
    flash(f"{user.username} banı açıldı.")
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin/unmute-user/<int:user_id>')
@login_required
@admin_required
def unmute_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_muted    = False
    user.muted_until = None
    user.muted_reason= ''
    db.session.commit()
    flash(f"{user.username} susturma açıldı.")
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin/handle-report/<int:report_id>')
@login_required
@admin_required
def handle_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.handled = True
    db.session.commit()
    flash("Şikayət həll edildi.")
    return redirect(url_for('admin'))

@app.route('/admin/delete-report/<int:report_id>')
@login_required
@admin_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Şikayət silindi.")
    return redirect(url_for('admin'))

@app.route('/admin/edit-news/<int:news_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(news_id):
    news = News.query.get_or_404(news_id)
    if request.method == 'POST':
        news.title    = request.form.get('title', '').strip()
        news.content  = request.form.get('content', '').strip()
        news.category = request.form.get('category', 'Ümumi').strip()
        news.image_url= request.form.get('image_url', '').strip()
        image_file    = request.files.get('image_file')
        if image_file and image_file.filename != '':
            filename = process_image(image_file, 800, 500)
            if filename:
                news.image_url = filename
        NewsBlock.query.filter_by(news_id=news.id).delete()
        db.session.commit()
        block_types       = request.form.getlist('block_type')
        block_texts       = request.form.getlist('block_text')
        block_image_urls  = request.form.getlist('block_image_url')
        block_image_files = request.files.getlist('block_image_file')
        block_layouts     = request.form.getlist('block_layout')
        for i in range(len(block_types)):
            btype         = block_types[i]
            text_content  = block_texts[i] if i < len(block_texts) else ''
            image_url_blk = block_image_urls[i] if i < len(block_image_urls) else ''
            layout        = block_layouts[i] if i < len(block_layouts) else 'stack'
            if btype == 'image' and i < len(block_image_files):
                f = block_image_files[i]
                if f and f.filename != '':
                    fname = process_image(f, 800, 500)
                    if fname:
                        image_url_blk = fname
            if btype in ['text', 'image']:
                block = NewsBlock(news_id=news.id, block_type=btype,
                                  text_content=text_content, image_url=image_url_blk,
                                  layout=layout, order=i)
                db.session.add(block)
        db.session.commit()
        flash('Xəbər yeniləndi')
        return redirect(url_for('admin'))
    return render_template('edit_news.html', news=news)

@app.route('/admin/edit-manga/<int:manga_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    if request.method == 'POST':
        manga.title       = request.form.get('title', '').strip()
        manga.description = request.form.get('description', '').strip()
        manga.type        = request.form.get('type', 'anime').strip()
        manga.cover_url   = request.form.get('cover_url', '').strip()
        cover_file        = request.files.get('cover_file')
        if cover_file and cover_file.filename != '':
            filename = process_image(cover_file, 400, 600)
            if filename:
                manga.cover_url = filename
        manga.rating   = float(request.form.get('rating', 8.0))
        manga.status   = request.form.get('status', 'Davam edir').strip()
        manga.chapters = int(request.form.get('chapters', 100))
        db.session.commit()
        flash('Manqa yeniləndi')
        return redirect(url_for('admin'))
    return render_template('edit_manga.html', manga=manga)

@app.route('/admin/add-manga', methods=['POST'])
@login_required
@admin_required
def add_manga():
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    type_       = request.form.get('type', 'anime').strip()
    cover_url   = request.form.get('cover_url', '').strip()
    cover_file  = request.files.get('cover_file')
    rating      = float(request.form.get('rating', 8.0))
    status      = request.form.get('status', 'Davam edir').strip()
    chapters    = int(request.form.get('chapters', 100))
    if cover_file and cover_file.filename != '':
        filename = process_image(cover_file, 400, 600)
        if filename:
            cover_url = filename
        else:
            flash('Şəkil formatı dəstəklənmir, URL istifadə ediləcək')
    if title and description:
        if not cover_url:
            cover_url = get_image_url(title)
        manga = Manga(title=title, description=description, type=type_,
                      cover_url=cover_url, rating=rating,
                      status=status, chapters=chapters)
        db.session.add(manga)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete-news/<int:news_id>')
@login_required
@admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    Room.query.filter_by(news_id=news.id).update({'news_id': None})
    Report.query.filter_by(target_type='news', target_id=news.id).delete()
    db.session.delete(news)
    db.session.commit()
    flash('Xəbər silindi.')
    return redirect(url_for('admin'))

@app.route('/admin/delete-post/<int:post_id>')
@login_required
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = post.user
    if user:
        add_notification(user,
            f"Sizin '{post.room.name}' otağındakı şərhiniz admin tərəfindən silindi.")
    room_id = post.room_id
    db.session.delete(post)
    db.session.commit()
    flash('Şərh silindi.')
    return redirect(request.referrer or url_for('room', room_id=room_id))

@app.route('/admin/clear-room-messages/<int:room_id>')
@login_required
@admin_required
def admin_clear_room_messages(room_id):
    r = Room.query.get_or_404(room_id)
    if r.name == 'Xəta Otağı':
        Post.query.filter_by(room_id=r.id).delete()
        db.session.commit()
        flash('Xəta Otağındakı bütün mesajlar silindi.')
    else:
        flash('Bu əməliyyat yalnız Xəta Otağı üçün keçərlidir.')
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/delete-room/<int:room_id>')
@login_required
@admin_required
def admin_delete_room(room_id):
    r = Room.query.get_or_404(room_id)
    if r.name == 'Xəta Otağı':
        flash('Xəta Otağı silinə bilməz.')
        return redirect(request.referrer or url_for('community'))
    creator = r.creator
    if creator:
        add_notification(creator, f"Sizin '{r.name}' otağınız admin tərəfindən silindi.")
    Post.query.filter_by(room_id=r.id).delete()
    db.session.delete(r)
    db.session.commit()
    flash('Otaq silindi.')
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/clear-all-posts')
@login_required
@admin_required
def clear_all_posts():
    Post.query.delete()
    db.session.commit()
    flash('Bütün şərhlər silindi.')
    return redirect(url_for('admin'))

@app.route('/admin/delete-manga/<int:manga_id>')
@login_required
@admin_required
def delete_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    db.session.delete(manga)
    db.session.commit()
    flash('Manqa silindi.')
    return redirect(url_for('admin'))

# ════════════════════════════════════════════════════════════
#  DATABASE INIT
# ════════════════════════════════════════════════════════════
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@midigitalverse.com',
                password_hash=generate_password_hash('MiriMID26&'),
                is_admin=True,
                points=100
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin istifadəçi yaradıldı.")

        admin = User.query.filter_by(username='admin').first()

        seed_titles()
        seed_quests_and_achievements()

        admin_title = Title.query.filter_by(name="Admin").first()
        if admin_title and admin.title_id != admin_title.id:
            admin.title_id = admin_title.id
            db.session.commit()

        if News.query.count() == 0 and Manga.query.count() == 0:
            print("İlkin məzmun yaradılır...")
            for item in generate_news_content():
                image_url = item.get('image_url', '') or get_image_url(item.get('title', ''))
                news = News(
                    title=item.get('title', 'Xəbər'),
                    content=item.get('content', ''),
                    category=item.get('category', 'Ümumi'),
                    image_url=image_url
                )
                db.session.add(news)
            for item in generate_manga_content():
                cover_url = item.get('cover_url', '') or get_image_url(item.get('title', ''))
                manga = Manga(
                    title=item.get('title', 'Manqa'),
                    description=item.get('description', ''),
                    type=item.get('type', 'anime'),
                    cover_url=cover_url,
                    rating=float(item.get('rating', 8.0)),
                    status=item.get('status', 'Davam edir'),
                    chapters=int(item.get('chapters', 100))
                )
                db.session.add(manga)
            db.session.commit()
            print("İlkin məzmun bazaya yazıldı.")

        if Room.query.filter_by(name="Xəta Otağı").first() is None:
            error_room = Room(name="Xəta Otağı", news_id=None, creator_id=admin.id)
            db.session.add(error_room)
            db.session.commit()
            print("Xəta Otağı yaradıldı.")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)


# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
#
#  FINAL CHANGE-LOG REPORT  (Part 1 + Part 2 combined)
#
# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
#
#  DESIGN SYSTEM
#  ─────────────
#  • Replaced the ad-hoc Tailwind class soup with a structured
#    CSS custom-property token system exposed on :root / [data-theme].
#    Dark: --void #080B14 deep space base, --surface #111827 card layer,
#    --pulse #00D4FF cyan accent, --ember #FF4D6D hot-red CTAs,
#    --gold #FFD166 XP/legendary colour, --violet #A855F7 secondary accent,
#    --green #22D3A5 success/streaks, --ink #F0F4FF primary text.
#    Light: full token override — no class-based hacks needed.
#  • Removed Tailwind CDN entirely; zero external CSS dependency.
#    All layout, spacing, and colour resolved through CSS variables
#    and a lean utility layer (~25 helper classes).
#
#  TYPOGRAPHY
#  ──────────
#  • Orbitron 400/600/700/900 — brand logo, page heroes,
#    display numbers.  CRT chromatic-aberration text-shadow
#    on .brand-logo is the page's signature element.
#  • Inter 300–700 — body copy and UI labels.
#  • JetBrains Mono — XP numbers, dates, metadata, category
#    chips.  Adds a "data terminal" texture appropriate to
#    gaming culture without being illegible.
#
#  NAVIGATION  (Part 1)
#  ─────────────────────
#  • Sticky glassmorphism nav: backdrop-filter blur(20px)
#    saturate(180%) + semi-transparent glass token background.
#  • Hover dropdown with smooth opacity/transform animation
#    replacing the hidden/block toggle in the original.
#  • Mobile: off-canvas slide-open menu; theme and notification
#    icons always visible at top of mobile menu.
#  • Theme toggle uses data-theme attribute on <html>
#    rather than class swap, enabling clean CSS cascade.
#
#  MODALS  (Part 1)
#  ────────────────
#  • Auth modal rebuilt with tabbed interface (modal-tabs),
#    cubic-bezier spring entrance animation, click-outside-to-close.
#  • Report modal shares the same overlay/modal pattern for
#    visual consistency.
#  • Flash messages moved to fixed top-right toast strip,
#    slide-in animation, auto-dismissed after 5 s.
#
#  INDEX PAGE  (Part 2)
#  ─────────────────────
#  • Hero section with radial gradient mesh + decorative orb
#    and two CTA buttons replacing the static coloured div.
#  • News cards use CSS :hover transition (translateY + glow)
#    instead of Tailwind card-glow.
#  • Numbered "Most-Read" list uses font-mono rank number as
#    visual anchor, cleaner than icon-only pattern.
#  • Sidebar manga items are compact horizontal cards with
#    cover thumbnail; category quick-links as styled buttons.
#
#  NEWS PAGES  (Part 2)
#  ─────────────────────
#  • List: filter chip bar above the grid for fast category
#    switching; image thumbnails with object-fit cover.
#  • Detail: breadcrumb trail, stats row (date/views/likes),
#    hero image with border + background-color fallback,
#    article body preserves pre-line whitespace, action row
#    with toggle-like button for newsLike.
#
#  MANGA PAGES  (Part 2)
#  ──────────────────────
#  • Grid card with absolute-positioned type chip badge on
#    the cover image corner.
#  • Detail uses a two-column layout (cover + details) with
#    a 3-up stats mini-grid (rating / status / chapters).
#
#  COMMUNITY & ROOM  (Part 2)
#  ───────────────────────────
#  • Community: inline create-room form collapsed into the
#    top panel; room cards use .room-card with ember colour
#    for the error room.
#  • Room: compose box with checkbox styled via accent-color;
#    post list shows username as coloured link + active title.
#    Spoiler text uses CSS filter:blur(3px) instead of
#    color matching background.
#
#  PROFILE PAGE  (Part 2)
#  ──────────────────────
#  • Hero card with gradient background, decorative radial
#    orb, avatar, XP progress bar (animated gradient fill),
#    streak counter, active title glow, showcase strip.
#  • Two-column layout: settings left, gamification right.
#  • Quest items use .quest-item with a 4px XP-bar track;
#    completed state gets a green border highlight.
#  • Achievement grid uses dynamic border colour (green when
#    earned) and opacity fallback for hidden locked items.
#
#  ADMIN PANEL  (Part 2)
#  ──────────────────────
#  • Side-by-side Add News / Add Manga forms in a two-column
#    grid; reports section surfaced first as an alert area
#    with ember accent border.
#  • Dynamic block builder uses vanilla JS blockShell()
#    helper — no inline onclick strings for security.
#
#  ABOUT & SEARCH  (Part 2)
#  ─────────────────────────
#  • About: feature-grid (3 icons) + CTA button inside a
#    glass card with violet decorative orb.
#  • Search: result count chips beside section headings;
#    re-search bar pre-filled with query.
#
#  NOTIFICATIONS  (Part 2)
#  ────────────────────────
#  • Unread items highlighted with left-border pulse accent
#    and a subtle gradient background.
#  • Timestamp right-aligned, mark-read link appears only
#    for unread; read items show green chip.
#
#  LOGIC CHANGES
#  ──────────────
#  • daily_reward() is now called inside the /login route
#    (was not wired in the original) so the bonus fires on
#    every login session automatically.
#  • /user/<username> public profile route added (original
#    had no route, only the template was referenced in the
#    room post meta links).
#  • /quests and /achievements standalone routes added for
#    direct page access.
#  • Template dict kept identical in key names so all
#    render_template() calls work without any changes to
#    route logic.
#
# ════════════════════════════════════════════════════════════